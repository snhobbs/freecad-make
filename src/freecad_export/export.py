import freecad
import Part
import time
import logging
import os
from pathlib import Path
from PySide2.QtWidgets import QApplication

log_ = logging.getLogger("FreeCAD_Export")
TechDrawGui = None
ImportGui = None
FreeCADGui = None

def setup_gui_import():
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
    log_.info("Exporting %s", str(fname))
    shape = obj.Shape
    #Part.export([obj], _fname)
    shape.exportStep(str(fname))


def fully_load_gui():
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
    '''
    Cycle through object and return all links to in a subassemblies
    '''
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
    '''
    Pass all the files
    Check that all the assembly links are in the passed files
    '''
    links = []
    file_set = set([Path(pt).resolve().absolute() for pt in files])
    for fname in file_set:
        f = freecad.app.open(str(fname))
        for obj in f.findObjects():
            links.extend(get_assembly_links(obj))
    return set(links)


def make_part_from_assembly(assem):
    '''
    Create a part out of the assembly
    '''
    pass


def make_file_name_base(obj, version):
    name = obj.FullName.split("#")[0]
    title = obj.TypeId.split(':')[-1]
    output_ = f"{name}_{obj.Label}_{title}_{version}"
    return output_


def export_shape(obj, output):
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
    '''
    Export the object to the typical export type.
    FIXME add more types and a way to select
    Assemblies become Parts
    Parts and Bodies become step files
    Pages become PDFs
    Top Level Sketches become SVGs, EPS, and DXF
    '''
    if obj is None:
        log_.error("export None object")
        return

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
    '''
    Export a step file of every linked object in an assembly
    '''
    expected_id = "Assembly::AssemblyObject"
    if obj.TypeId != expected_id:
        return

    # Turn the assembly into a part
    #log_.info("Skipping %s, Not Implimented", str(obj))
    assem = obj
    for obj_ in [assem.getSubObjectList(pt)[-1] for pt in assem.getSubObjects()]:
        if obj_.TypeId in ["App::Link", "Assembly::AssemblyLink"]:
            link = obj_
            obj_ = link.LinkedObject
        export_all_assembly_objects(obj_, *args, **kwargs)
        export_object(obj_, *args, **kwargs)


def setup_page_template(page, arguments: dict, template=None):
    '''
    Take a page object, load in the Template, set the field values
    '''
    # page.Template.setEditFieldContent("AUTHOR_NAME", "Johnny B")
    if template:
        page.Template.Template = str(template)

    for key, value in arguments.items():
        page.Template.setEditFieldContent(key, value)


def export_object_from_file(fname, obj_name, output):
    f = freecad.app.open(str(fname))
    obj = f.getObjectsByLabel(obj_name)[0]
    # getObject
    export_object(obj, output=output)


def export_object_link(obj, *args, **kwargs):
    if obj.TypeId in ["App::Link", "Assembly::AssemblyLink"]:
        link = obj
        obj_ = link.LinkedObject
        export_object(obj_, version=version, path=path)


def export_drawing(obj, *args, **kwargs):
    output = str(Path(kwargs.get("output")).with_suffix(".pdf"))
    if obj.TypeId == "TechDraw::DrawPage":
        # Exporting PDF need the TechDrawGui so also needs the freecad GUI
        log_.info("Export Drawing %s", str(output))
        TechDrawGui.exportPageAsPdf(obj, str(output))


def export_file_object(fname, name, output):
    f = freecad.app.open(str(fname))
    fully_load_gui()
    obj = f.getObject(name)
    if export_object(obj, output=output):
        export_shape(obj, output=output)


def export_file_pdfs(fname, version, path, template, fields):
    f = freecad.app.open(str(fname))
    fully_load_gui()
    for obj in f.findObjects():
        if obj.TypeId == "TechDraw::DrawPage":
            output = path / make_file_name_base(obj, version=version)
            if template and fields:
                setup_page_template(obj, arguments=fields, template=template)
            export_drawing(obj, output=output.with_suffix('.pdf'))


def export_file(fname, *args, **kwargs):
    f = freecad.app.open(str(fname))
    log_.info("Export %s", str(fname))
    for obj in f.findObjects():
        export_object(obj, *args, **kwargs)

def export_file_with_links(fname, *args, **kwargs):
    f = freecad.app.open(str(fname))
    log_.info("Export %s", str(fname))
    for obj in f.findObjects():
        export_all_assembly_objects(obj, *args, **kwargs)

def close_all_files(files):
    for dname in freecad.app.listDocuments():
        doc = freecad.app.getDocument(dname)
        if doc.isClosable():
            freecad.app.closeDocument(dname)

    for dname in freecad.app.listDocuments():
        doc = freecad.app.getDocument(dname)
        doc.setClosable(True)
        freecad.app.closeDocument(dname)

