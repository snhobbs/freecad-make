import sys
import logging
import os
from pathlib import Path
import click
from . import export

log_ = logging.getLogger("FreeCAD_Export")


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
    log_.setLevel(logging.INFO)
    if debug:
        log_.setLevel(logging.DEBUG)


@click.argument("files", nargs=-1, required=True)
@gr1.command("check-links")
def cli_check_assembly_links(files):
    files = [Path(pt).resolve().absolute() for pt in files]
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
@click.option("--single-file", is_flag=True, help="Exports all the components used within a specific assembly.")
@click.option("--single-directory", is_flag=True, help="Outputs all files into a single directory.")
@click.option("--path", "path", type=str, required=False)
@click.argument("files", nargs=-1, required=True)
@gr1.command("export", help="Export all objects associated with a given file.")
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
    for fname in all_files:
        path_ = path
        if not single_directory:
            path_ = path / fname.stem
        if not path_.exists():
            os.mkdir(path_)
        if pdfs:
            export.export_file_pdfs(fname, version=version, path=path_)
        else:
            if single_file:
                export.export_file_with_links(fname, version=version, path=path_)
            export.export_file(fname, version=version, path=path_)
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

