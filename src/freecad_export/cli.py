import sys
import click
import logging
import os
from pathlib import Path
from . import export

log_ = None


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
    files = [Path(pt).resolve().absolute() for pt in set(files)]
    linked_files = export.get_all_file_assembly_links(files)
    linked_files = [Path(pt).resolve().absolute() for pt in linked_files]

    set_diff = set(linked_files).difference(set(files))
    if len(set_diff):
        log_.error("Not all linked files found %s", str(set_diff))
        sys.exit(1)

    else:
        log_.info("All links accounted for: %s", str(linked_files))
    export.close_all_files(files)


#@click.option("--fname", required=True)
@click.option("--version", default="X.X.X")
@click.option("--pdfs", is_flag=True)
@click.option("--steps", is_flag=True)
@click.option("--path", "path", required=False)
@click.argument("files", nargs=-1, required=True)
@gr1.command("export-assemblies", help="Export all objects linked to in an assembly")
def cli_export_assemblies(version, pdfs, steps, path, files):
    if path is None:
        path = Path(os.getcwd())

    path = Path(path).absolute()

    all_files = set(list(files))
    all_files = set([Path(pt).resolve().absolute() for pt in all_files])
    stems = [pt.stem for pt in all_files]
    duplicates = set([pt for pt in stems if stems.count(pt) > 1])

    if len(duplicates):
        log_.error("Duplicated file stems %s, \n%s", str(duplicates), str(all_files))

    else:
        export.setup_gui_import()

        for file in all_files:
            path_ = path / file.stem
            if not path_.exists():
                os.mkdir(path_)
                export.export_file(file, version=version, path=path_)
        log_.info("Finished all files")

    export.close_all_files(files)

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
    # export.close_all_files(files)

    all_files = set(list(files)) # + list(linked_files))
    all_files = set([Path(pt).resolve().absolute() for pt in all_files])
    stems = [pt.stem for pt in all_files]
    duplicates = set([pt for pt in stems if stems.count(pt) > 1])

    if len(duplicates):
        log_.error("Duplicated file stems %s, \n%s", str(duplicates), str(all_files))

    else:
        export.setup_gui_import()

        for file in all_files:
            path_ = path / file.stem
            if not path_.exists():
                os.mkdir(path_)
                export.export_file(file, version=version, path=path_)
        log_.info("Finished all files")

    export.close_all_files(files)


def main():
    gr1()


if __name__ == "__main__":
    main()

