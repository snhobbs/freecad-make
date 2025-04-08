# FreeCAD-Make

Build function for FreeCAD projects, designed to automate the process of exporting assemblies, TechDraw pages, and STEP files for structured project releases. It provides a standardized way to extract and organize components from FreeCAD files. This is similar in spirit to the kicad-make project [here](www.github.com/snhobbs/kicad-make).

## Features
+ Export all TechDraw pages from a set of files
+ Export all solid objects and collections of objects, including linked objects in Assemblies.
+ Crawl Assembly link trees to verify that links point to known files.
+ Maintain consistent naming and organization of exported components.
+ Export STEP files for assemblies, parts, bodies, and features (any solid object).
+ Selectively export a specific page or object within a project for use in Makefiles.


## Functions
### `check-links`
Checks that all linked objects in an assembly reference files are included in the build. This ensures assemblies are self-contained and correctly linked.

### `export-object`
Exports a specific named object from a given file. Useful for Makefile integration when targeting individual components.

#### Example: Makefile Using `export-object`
```make
_SOURCE=$(abspath ${SOURCE})
VERSION=0.1.0

FILES = \
    PartDesignExample_${VERSION}.step \
    PartDesignExample_Drawing_${VERSION}.pdf

.PHONY: all
all: ${FILES}

.PHONY: clean
clean:
    -rm ${FILES}

# Generic rule exporting the object in the FreeCAD file that has the same name as the file.
%_${VERSION}.step: ${_SOURCE}/%.FCStd
    -freecad_export export-object --path $@ --fname $< --object $*

# Generic rule exporting the a page in the FreeCAD file that has the same name ${FILENAME}-Drawing.
%_Drawing_${VERSION}.pdf: ${_SOURCE}/%.FCStd
    -freecad_export export-object --path $@ --fname $< --object $*-Drawing
```

### `export`
Handles bulk exporting, including link crawling and structured output. Options include:
- **Default Mode:** Crawls assembly links and exports all referenced components. Each FreeCAD file is exported in it's own directory.
- **Single Directory Mode (`--single-directory`)**: Outputs all files into a single directory.
- **Single File Mode (`--single-file`)**: Exports all the components used within a specific assembly.
- **PDF-Only Mode (`--pdf-only`)**: Skips STEP file generation and only exports TechDraw pages.

Generated file names follow the format:
```
{FILENAME_STEM}_{OBJECT_NAME}_{IDTYPE}_{VERSION}.{EXTENSION}
```
For example, `waveguide_foot` PartDesign::Body in `waveguide_foot.FCStd` exports as:
```
waveguide_foot_waveguide_foot_Body_0.1.step
```
`waveguide_foot-Drawing` TechDraw::DrawPage in `waveguide_foot.FCStd` exports as:
```
waveguide_foot_Drawing_DrawPage_0.1.pdf
```

#### Example: Export All TechDraw Pages to a Single Directory
```sh
> freecad_export export --single-directory --pdf-only --path ./ --version 0.1.0 waveguide.FCStd
> ls
waveguide_waveguide-Drawing_DrawPage_0.1.pdf
probe_probe-Drawing_DrawPage_0.1.pdf
waveguide_spacer_waveguide-spacer-Drawing_DrawPage_0.1.pdf
waveguide_foot_waveguide_foot-Drawing_DrawPage_0.1.pdf
waveguide_waveguide-Drawing_DrawPage_0.1.pdf
```
This command will crawl all linked files, load any TechDraw pages, and export them into a single directory.


#### Example: Export All Objects and Drawings from an Assembly into a Directory
```sh
> freecad_export export --single-file --path ./ --version 0.1.0 waveguide.FCStd
> ls
waveguide
> cd waveguide && ls
probe_probe_Body_0.1.step
waveguide_spacer_waveguide-spacer_Body_0.1.step
waveguide_waveguide_AssemblyObject_0.1.step
waveguide_foot_waveguide_foot_Body_0.1.step
waveguide_waveguide-Drawing_DrawPage_0.1.pdf
```
This export all STEP files and TechDraw PDFs associated with the assembly (included in or linked).

#### Example: Export All Objects and Drawings from a Set of Files

This command takes a list of FreeCAD files, crawls all the links, and exports
all the components in each of these files. You can use it to export all the objects not include in single-file mode by calling with just one Assembly and using the --single-directory option.

```sh
> freecad_export export --path ./ --version 0.1.0 waveguide.FCStd
> ls
waveguide-spacer
waveguide_foot
waveguide
probe
> cd probe && ls
probe_probe-Drawing_DrawPage_0.1.pdf
probe_probe_Body_0.1.step
```

## Project Organization
The crawling functions are most useful for archiving and verification. A typical workflow involves storing each designed object in its own file, with associated drawings included. Different types of drawings can be used for:
- **Quoting** (RFQ Drawings)
- **Engineering Discussions** (General Assembly or Detail Drawings)
- **Assembly Documentation**

This approach maintains consistency across projects while automating file exports.

When deciding where to store drawings and details, a recommended method is to place them at the lowest logical level. If a drawing pertains to a single object, it should be stored within that object's design file rather than in an assembly file.


## Further Upgrades
+ Make Part Object out of Assemblies. Strip all links and export a FreeCAD file that has all the objects enclosed.


## Trouble Shooting
### Seg Faults at Startup
+ Check the configuration files and macros. I had an old installation that caused the AppImage to just crash on startup. Removing config files at ${HOME}/.local/share/FreeCAD/fixed it. Call ```freecad --dump-config``` to find where your macros and config files are.

### Step File Export Seg Faults
+ Hidden parts in a model results in a seg fault for some reason. You'll need to remove those parts or unhide them. This is a known issue: https://github.com/FreeCAD/FreeCAD/issues/18056
