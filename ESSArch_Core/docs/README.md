# ESSArch Core Documentation

## Requirements
Install requirements using `pip install -r requirements_docs.txt` in the parent folder or run the following commands

```
$ pip install sphinx==1.5.2
$ pip install sphinxtogithub==1.1.0

```

## Generating documentation

Start by generating the source files

```
$ sphinx-apidoc -f -o source .. ../**/migrations
```

Then create the documentation files

```
$ make html
```

The output will be available in `build/html`
