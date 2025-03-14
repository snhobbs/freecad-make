import click
import freecad
import Part
import time
import logging
import sys
from pathlib import Path

log_ = None
TechDrawGui = None

'''
+ Check the links are in the file list
'''
def export_shape_to_step(obj, fname):
    log_.info("Exporting %s", str(fname))
    shape = obj.Shape
    #Part.export([obj], _fname)
    shape.exportStep(str(fname))

def fully_load_gui():
    while not freecad.app.ActiveDocument:
        FreeCADGui.updateGui()
        time.sleep(0.1)

    for _ in range(10):
        FreeCADGui.updateGui()
        time.sleep(0.1)
    freecad.app.ActiveDocument.recompute()
    FreeCADGui.updateGui()
    w = FreeCADGui.getMainWindow()
    w.repaint()

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


def export_object(obj, version="X.X.X", path=Path('./'), export_step=False):
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

    if obj.TypeId == "TechDraw::DrawPage":
        # Exporting PDF need the TechDrawGui so also needs the freecad GUI
        name = obj.FullName.replace("#", "_")
        _base_name = f"{obj.Label}_{name}_Drawing_{version}.pdf"
        _fname = str(path / _base_name)
        log_.info("Export Drawing %s", _fname)

        fully_load_gui()
        TechDrawGui.exportPageAsPdf(obj, _fname)


    elif obj.TypeId == "Assembly::AssemblyObject":
        # Turn the assembly into a part
        #log_.info("Skipping %s, Not Implimented", str(obj))
        assem = obj
        #for obj_ in [assem.getSubObjectList(pt)[-1] for pt in assem.getSubObjects()]:
        #    export_object(obj_, version=version, path=path)
        # We are not exporting the assembly subsections. Those are checked
        # for the links being exported only

        name = obj.FullName.replace("#", "_")
        _fname = f"{obj.Label}_{name}_Assembly_{version}.step"
        export_shape_to_step(obj, str(path / _fname))
        part = make_part_from_assembly(assem)
        # export_object(part, version=version, path=path)

    elif obj.TypeId in ["App::Link", "Assembly::AssemblyLink"]:
        # link = obj
        # obj_ = link.LinkedObject
        # export_object(obj_, version=version, path=path)
        log_.warning("Object skipped %s: %s, %s", obj.FullName, obj.TypeId, str(obj))


    elif obj.TypeId in ["PartDesign::Body"]:
        name = obj.FullName.replace("#", "_")
        _fname = f"{obj.Label}_{name}_Body_{version}.step"
        export_shape_to_step(obj, str(path / _fname))

    elif obj.TypeId in ["PartDesign::Part", "App::Part"]:
        '''
        Export the part and all bodies
        '''
        # name = obj.FullName.replace("#", "_")
        # Part.export([obj], f"{name}_{version}.step")
        # FIXME add iteration through subbodies
        # FIXME add option to export to Parts to .FCStd or not
        part = obj
        for obj_ in [part.getSubObjectList(pt)[-1] for pt in part.getSubObjects()]:
            export_object(obj_, version=version, path=path)

        name = obj.FullName.replace("#", "_")
        _fname = f"{obj.Label}_{name}_Part_{version}.step"
        export_shape_to_step(obj, str(path / _fname))

    elif obj.TypeId in ["Sketcher::SketchObject"]:
        name = obj.FullName.replace("#", "_")
        _fname = f"{obj.Label}_{name}_Sketch_{version}"
        log_.warning("Sketch Export not implimented")


    elif hasattr(obj, "Shape"):
        shape = obj.Shape
        def object_is_exportable(obj_):
            if not hasattr(obj, "Shape"):
                return 0
            if obj_.TypeId in ["App::Plane", "App::Line", "App::Origin", "Sketcher::SketchObject"]:
                return 0
            if obj.Shape.Area == 0:
                return 0
            return 1

        if not object_is_exportable(obj):
            log_.warning("Object skipped %s: %s, %s", obj.FullName, obj.TypeId, str(obj))
        else:
            log_.debug("Exporting %s: %s, %s", obj.Label, obj.TypeId, str(obj))
            name = obj.FullName.split("#")[0]
            _fname = f"{name}_{obj.Label}_Shape_{version}.step"
            export_shape_to_step(obj, str(path / _fname))
    else:
        log_.warning("Object skipped %s: %s, %s", obj.FullName, obj.TypeId, str(obj))


def export_file(fname, *args, **kwargs):
    f = freecad.app.open(str(fname))
    log_.info("Export %s", str(fname))
    for obj in f.findObjects():
        export_object(obj, *args, **kwargs)


@click.group()
def gr1():
    pass

@click.argument("files", nargs=-1, required=True)
@gr1.command("check-links")
def cli_check_assembly_links(files):
    files = [Path(pt).resolve().absolute() for pt in set(files)]
    linked_files = get_all_file_assembly_links(files)
    linked_files = [Path(pt).resolve().absolute() for pt in linked_files]

    set_diff = set(linked_files).difference(set(files))
    if len(set_diff):
        log_.error("Not all linked files found %s", str(set_diff))
        sys.exit(1)

    else:
        log_.info("All links accounted for: %s", str(linked_files))
    close_all_files(files)


def close_all_files(files):
    for dname in freecad.app.listDocuments():
        doc = freecad.app.getDocument(dname)
        if doc.isClosable():
            freecad.app.closeDocument(dname)

    for dname in freecad.app.listDocuments():
        doc = freecad.app.getDocument(dname)
        doc.setClosable(True)
        freecad.app.closeDocument(dname)


#@click.option("--fname", required=True)
@click.option("--version", default="X.X.X")
@click.option("--pdfs", is_flag=True)
@click.option("--steps", is_flag=True)
@click.option("--path", "path", required=False)
@click.argument("files", nargs=-1, required=True)
@gr1.command("export")
def cli_export(version, pdfs, steps, path, files):
    if path is None:
        path = Path(os.getcwd())

    path = Path(path).absolute()

    # linked_files = get_all_file_assembly_links(files)
    # close_all_files(files)

    all_files = set(list(files)) # + list(linked_files))
    all_files = set([Path(pt).resolve().absolute() for pt in all_files])
    stems = [pt.stem for pt in all_files]
    duplicates = set([pt for pt in stems if stems.count(pt) > 1])

    if len(duplicates):
        log_.error("Duplicated file stems %s, \n%s", str(duplicates), str(all_files))

    else:
        import FreeCADGui
        FreeCADGui.showMainWindow()
        global TechDrawGui
        import TechDrawGui as TechDrawGui_
        TechDrawGui = TechDrawGui_

        for file in all_files:
            path_ = path / file.stem
            if not path_.exists():
                os.mkdir(path_)
                export_file(file, version=version, path=path_)
        log_.info("Finished all files")

    close_all_files(files)


# Make a directory for each Freecad file so the object will be unique
def make_file_name(pt, version, ext, date):
    fname = f"{pt.Name}_{version}_{date}.{ext}"


def main():
    logging.basicConfig()
    global log_
    log_ = logging.getLogger("FreeCAD_Export")
    log_.setLevel(logging.DEBUG)
    gr1()


if __name__ == "__main__":
    main()

