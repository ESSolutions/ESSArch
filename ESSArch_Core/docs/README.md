# ESSArch Core Documentation

## Installing Requirements
Install requirements from `docs` in `setup.py`

```
$ pip install ESSArch_Core[docs]
```

## Translating documentation

* Create .pot-files

```
$ make gettext
```

* Create and/or update .po-files

```
$ sphinx-intl update -p _build/gettext -l {lang}
```

* Edit files in .po-files in `locale/{lang}/LC_MESSAGES/`

## Generating documentation

Run the following where format is either `html` or `pdf`

```
$ make {format} LANGUAGE="{lang}"
```

The output will be available in `_build`
