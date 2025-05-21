import time
import logging
from pathlib import Path
import freecad
# import Part
from PySide2.QtWidgets import QApplication

log_ = logging.getLogger("FreeCAD_Export")
TechDrawGui = None
ImportGui = None
FreeCADGui = None

def setup_gui_import():
    """
    Load and initialize the FreeCAD GUI modules required for exporting operations.

    This function imports and initializes the FreeCADGui, TechDrawGui, and ImportGui
    modules, and ensures the FreeCAD main window is shown.

    Imports are hidden as they take time to load and are not required for all operations.
    """
    global FreeCADGui
    import FreeCADGui as FreeCADGui_
    FreeCADGui = FreeCADGui_

    FreeCADGui.showMainWindow()

    global TechDrawGui
    import TechDrawGui as TechDrawGui_
    TechDrawGui = TechDrawGui_

    global ImportGui
    import ImportGui as ImportGui_
    ImportGui = ImportGui_


def export_shape_to_step(obj, fname):
    """
    Export the shape of a FreeCAD object to a STEP file.

    Parameters:
        obj (FreeCAD object): The object whose shape will be exported.
        fname (Path or str): The output STEP file path.
    """
    log_.info("Exporting %s", str(fname))
    shape = obj.Shape
    #Part.export([obj], _fname)
    shape.exportStep(str(fname))


def fully_load_gui():
    """
    Wait until the GUI is fully initialized and the active document is recomputed.

    This function ensures that the GUI is loaded and all pending events are processed
    before proceeding with further GUI-based operations like exporting PDFs.
    """
    while not freecad.app.ActiveDocument:
        FreeCADGui.updateGui()
        time.sleep(0.1)

    FreeCADGui.updateGui()
    freecad.app.ActiveDocument.recompute()

    for i in range(1000):
        time.sleep(5e-3)
        while QApplication.instance().hasPendingEvents():
            FreeCADGui.updateGui()

    w = FreeCADGui.getMainWindow()
    w.repaint()
    time.sleep(5)

def get_assembly_links(obj):
    """
    Recursively gather all file links used in an assembly object.

    Parameters:
        obj (FreeCAD object): The object to inspect for linked subassemblies.

    Returns:
        list of str: List of file paths referenced by the assembly.
    """
    log_.debug("get_assembly_links: %s", obj.FullName)
    links = []
    if obj.TypeId in ["App::Link", "Assembly::AssemblyLink"]:
        link = obj
        obj_ = link.LinkedObject
        links.append(obj_.Document.FileName)
        links.extend(get_assembly_links(obj_))
    elif obj.TypeId == "Assembly::AssemblyObject":
        assem = obj
        links.append(assem.Document.FileName)
        objects = [assem.getSubObjectList(pt)[-1] for pt in assem.getSubObjects()]
        for subobj in objects:
            links.extend(get_assembly_links(subobj))
    else:
        log_.debug("Skip %s (%s), no links", obj.FullName, obj.TypeId)
    return links


def get_all_file_assembly_links(files):
    """
    For a given list of FreeCAD files, gather all assembly file links used.

    Parameters:
        files (list of str or Path): Paths to FreeCAD files.

    Returns:
        set of Path: Set of all resolved file paths linked within the assemblies.
    """
    links = []
    file_set = set([Path(pt).resolve().absolute() for pt in files])
    for fname in file_set:
        f = freecad.app.open(str(fname))
        for obj in f.findObjects():
            links.extend(get_assembly_links(obj))
    return set(links)


def make_part_from_assembly(assem):
    """
    Convert an assembly object into a single part representation.

    Parameters:
        assem (FreeCAD object): The assembly object.

    Returns:
        Part object or None: The generated part object (Not yet implemented).
    """
    pass


def make_file_name_base(obj, version):
    """
    Generate a base filename for exported files based on object metadata.

    Parameters:
        obj (FreeCAD object): The object to be exported.
        version (str): A version string to append to the filename.

    Returns:
        str: A sanitized and informative filename base.
    """
    name = obj.FullName.split("#")[0]
    title = obj.TypeId.split(':')[-1]
    output_ = f"{name}_{obj.Label}_{title}_{version}"
    return output_


def export_shape(obj, output):
    """
    Export a single object's shape as a STEP file, if it's valid.

    Parameters:
        obj (FreeCAD object): The object to export.
        output (Path): Output file path base (extension added automatically).

    Returns:
        int: 0 if export was attempted, 1 if object was invalid or skipped.
    """
    def object_is_exportable(obj_):
        if not hasattr(obj_, "Shape"):
            return 0
        if obj_.TypeId in ["App::Plane", "App::Line", "App::Origin", "Sketcher::SketchObject"]:
            return 0
        if obj_.Shape.Area == 0:
            return 0
        return 1

    if not hasattr(obj, "Shape"):
        return 1

    shape = obj.Shape
    if not object_is_exportable(obj):
        log_.warning("Object skipped %s: %s, %s", obj.FullName, obj.TypeId, str(obj))
    else:
        log_.debug("Exporting %s: %s, %s", obj.Label, obj.TypeId, str(obj))
        export_shape_to_step(obj, str(output.with_suffix(".step")))
    return 0


def export_object(obj, version="X.X.X", path=Path('./'), output=None):
    """
    Export a FreeCAD object to the appropriate output format based on its type.

    FIXME add more types and a way to select
    Assemblies become Parts
    Parts and Bodies become step files
    Pages become PDFs
    Top Level Sketches become SVGs, EPS, and DXF

    Parameters:
        obj (FreeCAD object): The object to export.
        version (str): A version identifier to use in filenames.
        path (Path): Output directory.
        output (Path, optional): Specific output path to use instead of auto-generating.

    Returns:
        int: 0 if export succeeded, 1 if skipped or failed.
    """
    if obj is None:
        log_.error("export None object")
        return 1

    log_.info("Export %s, %s", obj.FullName, str(obj))

    if output is None:
        output_ = path / make_file_name_base(obj, version=version)
    else:
        output_ = output

    if obj.TypeId == "TechDraw::DrawPage":
        fully_load_gui()
        export_drawing(obj, output=output_.with_suffix(".pdf"))

    if obj.TypeId == "Assembly::AssemblyObject":
        # Turn the assembly into a part
        assem = obj
        # We are not exporting the assembly subsections. Those are checked
        # for the links being exported only
        ImportGui.export([obj], str(output_.with_suffix(".step")))
        part = make_part_from_assembly(assem)
        # export_object(part, version=version, path=path)

    elif obj.TypeId in ["PartDesign::Body"]:
        export_shape_to_step(obj, str(output_.with_suffix(".step")))

    elif obj.TypeId in ["PartDesign::Part", "App::Part"]:
        '''
        Export the part and all bodies
        '''
        # name = obj.FullName.split("#")[0]
        # Part.export([obj], f"{name}_{version}.step")
        # FIXME add iteration through subbodies
        # FIXME add option to export Parts to .FCStd or not
        part = obj
        for obj_ in [part.getSubObjectList(pt)[-1] for pt in part.getSubObjects()]:
            export_object(obj_, output=output_)

        name = obj.FullName.split("#")[0]
        ImportGui.export([obj], str(output_.with_suffix(".step")))

    elif obj.TypeId in ["Sketcher::SketchObject"]:
        log_.warning("Sketch Export not implimented")
        return 1

    else:
        log_.warning("Object skipped %s: %s, %s", obj.FullName, obj.TypeId, str(obj))
        return 1
    return 0


def export_all_assembly_objects(obj, *args, **kwargs):
    """
    Recursively export all objects in an assembly, following links.

    Parameters:
        obj (FreeCAD object): Assembly object to process.
        *args, **kwargs: Passed to export_object.
    """
    expected_id = "Assembly::AssemblyObject"
    if obj.TypeId != expected_id:
        return

    assem = obj
    for obj_ in [assem.getSubObjectList(pt)[-1] for pt in assem.getSubObjects()]:
        if obj_.TypeId in ["App::Link", "Assembly::AssemblyLink"]:
            link = obj_
            obj_ = link.LinkedObject
        export_all_assembly_objects(obj_, *args, **kwargs)
        export_object(obj_, *args, **kwargs)


def setup_page_template(page, arguments: dict, template=None):
    """
    Apply a title block template and field data to a TechDraw page.

    Parameters:
        page (TechDraw::DrawPage): The drawing page object.
        arguments (dict): Dictionary of field keys and values to apply.
        template (Path, optional): Optional template file path to assign.
    """
    if template:
        page.Template.Template = str(template)

    for key, value in arguments.items():
        page.Template.setEditFieldContent(key, value)


def export_object_from_file(fname, obj_name, output):
    """
    Open a file and export a named object to a specified output.

    Parameters:
        fname (str or Path): FreeCAD file path.
        obj_name (str): Label of the object to export.
        output (Path): Output file base path.
    """
    f = freecad.app.open(str(fname))
    obj = f.getObjectsByLabel(obj_name)[0]
    export_object(obj, output=output)


def export_object_link(obj, *args, **kwargs):
    """
    Resolve and export a linked object from a Link or AssemblyLink.

    Parameters:
        obj (FreeCAD object): Link object pointing to the real object.
        *args, **kwargs: Passed to export_object.
    """
    if obj.TypeId in ["App::Link", "Assembly::AssemblyLink"]:
        link = obj
        obj_ = link.LinkedObject
        export_object(obj_, version=version, path=path)


def export_drawing(obj, *args, **kwargs):
    """
    Export a TechDraw page object to PDF using the GUI.

    Parameters:
        obj (TechDraw::DrawPage): The drawing object to export.
        output (Path): Output path for the PDF file.
    """
    output = str(Path(kwargs.get("output")).with_suffix(".pdf"))
    if obj.TypeId == "TechDraw::DrawPage":
        log_.info("Export Drawing %s", str(output))
        TechDrawGui.exportPageAsPdf(obj, str(output))


def export_file_object(fname, name, output):
    """
    Open a file and export a specific named object, falling back to shape export if needed.

    Parameters:
        fname (str or Path): FreeCAD file path.
        name (str): Name of the object within the file.
        output (Path): Output file path.
    """
    f = freecad.app.open(str(fname))
    fully_load_gui()
    obj = f.getObject(name)
    if export_object(obj, output=output):
        export_shape(obj, output=output)


def export_file_pdfs(fname, version, path, template, fields):
    """
    Export all TechDraw pages in a file as PDFs with template and metadata fields.

    Parameters:
        fname (str or Path): FreeCAD file path.
        version (str): Version string to include in filenames.
        path (Path): Output directory.
        template (Path): Template to apply to each page.
        fields (dict): Title block field values to set.
    """
    f = freecad.app.open(str(fname))
    fully_load_gui()
    for obj in f.findObjects():
        if obj.TypeId == "TechDraw::DrawPage":
            output = path / make_file_name_base(obj, version=version)
            if template and fields:
                setup_page_template(obj, arguments=fields, template=template)
            export_drawing(obj, output=output.with_suffix('.pdf'))


def export_file(fname, *args, **kwargs):
    """
    Export all exportable objects in a FreeCAD file.
    Parts exported under the assembly

    Parameters:
        fname (str or Path): FreeCAD file path.
        *args, **kwargs: Passed to export_object.
    """
    f = freecad.app.open(str(fname))
    log_.info("Export %s", str(fname))
    for obj in f.findObjects():
        export_object(obj, *args, **kwargs)

def export_file_with_links(fname, *args, **kwargs):
    """
    Export all linked objects in assemblies in a FreeCAD file.
    Parts exported under the linked files

    Parameters:
        fname (str or Path): FreeCAD file path.
        *args, **kwargs: Passed to export_object.
    """
    f = freecad.app.open(str(fname))
    log_.info("Export %s", str(fname))
    for obj in f.findObjects():
        export_all_assembly_objects(obj, *args, **kwargs)

def close_all_files(files):
    """
    Close all open FreeCAD documents, forcing closability if necessary.

    Parameters:
        files (list): Unused; maintained for interface compatibility.
    """
    for dname in freecad.app.listDocuments():
        doc = freecad.app.getDocument(dname)
        if doc.isClosable():
            freecad.app.closeDocument(dname)

    for dname in freecad.app.listDocuments():
        doc = freecad.app.getDocument(dname)
        doc.setClosable(True)
        freecad.app.closeDocument(dname)

