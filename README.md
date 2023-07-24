# disk-scan
A Python library to scan disks and clean it up.

## Install
```
$ make install
```

## For Developers
```
$ make develop
$ source .env/bin/activate
```

## Usage
```
$ ./scan
Usage: disk.py [OPTIONS] COMMAND [ARGS]...

Commands:
  bigfiles     Find big files.
  byname       Find files with names.
  bysuffix     Filter out files with suffixes.
  duplicate    Find duplicated files.
  emptydirs    Find empty directories.
  renamedirs   Replace old name with new name, can be a partial replace.
  renamefiles  Replace old name with new name, can be a partial replace.
```

## Examples

**Find duplicated files**
```bash
# Scan and print to screen
./scan.py duplicate ~/Downloads
# Scan and print to file
./scan.py duplicate ~/Downloads --json=output.json
```

**Find large files > 100MB**
```bash
# Scan and print to screen
./scan.py bigfiles ~/Downloads --size=100
# Scan and print to file
./scan.py bigfiles ~/Downloads --json=output.json
```

**Find files by suffix jpg or png**
```bash
# Scan and print to screen
./scan.py bysuffix ~/Downloads -s jpeg -s png
# Scan and print to file
./scan.py bysuffix ~/Downloads -s mp4 --json=output.json
```

**Find files by name**
```bash
# Scan and print to screen
./scan.py byname ~/Downloads -n sunshine -n apple
# Scan and print to file
./scan.py byname ~/Downloads -n juice --json=output.json
```

**Find empty directories**
```bash
./scan.py emptydirs ~/Downloads
```

**Rename directory, replace old string with new string**
```bash
./scan.py renamedirs ~/Downloads --old ninja --new gundam
```

**Rename files, replace old string with new string**
```bash
./scan.py renamefiles ~/Downloads --old ninja --new gundam
```

**Normalize file names**
```bash
./scan.py normalize ~/Downloads --regex *.jpg
```

```bash
./scan.py normalize ~/Downloads --only-media
```

**Remove files**
```bash
./remover.py automatic --json=[?.json]
```

```bash
./remover.py interactive --json=[?.json]
```