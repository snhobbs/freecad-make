import sys
import click
import logging
import os
from pathlib import Path
from . import export

log_ = None


def expand_linked_files(files):
    linked_files = export.get_all_file_assembly_links(files)
    export.close_all_files(files)
    all_files = set(list(files) + list(linked_files))
    all_files = set([Path(pt).resolve().absolute() for pt in all_files])
    return all_files


@click.group()
@click.option("--debug", is_flag=True)
def gr1(debug):
    logging.basicConfig()
    global log_
    log_ = logging.getLogger("FreeCAD_Export")
    log_.setLevel(logging.INFO)
    if debug:
        log_.setLevel(logging.DEBUG)


@click.argument("files", nargs=-1, required=True)
@gr1.command("check-links")
def cli_check_assembly_links(files):
    all_files = expand_linked_files(files)

    set_diff = set(all_files).difference(set(files))
    if len(set_diff):
        log_.error("Not all linked files found %s", str(set_diff))
        sys.exit(1)

    else:
        log_.info("All links accounted for: %s", str(all_files))
    export.close_all_files(files)


@click.option("--version", default="X.X.X")
@click.option("--pdf-only", "pdfs", is_flag=True)
@click.option("--single-file", is_flag=True)
@click.option("--single-directory", is_flag=True)
@click.option("--path", "path", type=str, required=False)
@click.argument("files", nargs=-1, required=True)
@gr1.command("export")
def cli_export(version, pdfs, single_file, single_directory, path, files):
    if path is None:
        path = Path(os.getcwd())
    path = Path(path).resolve().absolute()

    all_files = [Path(pt) for pt in files]
    if not single_file:
        all_files = expand_linked_files(files)

    stems = [pt.stem for pt in all_files]
    duplicates = set([pt for pt in stems if stems.count(pt) > 1])
    if len(duplicates):
        log_.error("Duplicated file stems %s, \n%s", str(duplicates), str(all_files))
        export.close_all_files(files)
        return

    export.setup_gui_import()
    for file in all_files:
        path_ = path
        if not single_directory:
            path_ = path / file.stem
        if not path.exists():
            os.mkdir(path_)
        if pdfs:
            export.export_file_pdfs(file, version=version, path=path_)
        else:
            export.export_file(file, version=version, path=path_)
    log_.info("Finished all files")
    export.close_all_files(files)


@click.option("--fname", required=True)
@click.option("--object", "-o", "obj_name", required=True)
@click.option("--version", default="X.X.X")
@click.option("--path", "path", required=False)
@gr1.command("export-object", help="Export a specific named object in the named file")
def cli_export_object(fname, obj_name, version, path):
    if path is None:
        path = Path(os.getcwd())
    path = Path(path).resolve().absolute()
    export.setup_gui_import()
    export.export_object_from_file(fname, obj_name, output=path)
    export.close_all_files([fname])


def main():
    gr1()


if __name__ == "__main__":
    main()

