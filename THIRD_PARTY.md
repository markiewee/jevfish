# Third-party components

| Component | Licence | Why it is here |
|---|---|---|
| [MiroFish](https://github.com/666ghj/MiroFish) | AGPL-3.0 | JevFish reimplements its five-stage pipeline. The upstream trees are kept unmodified |
| [typesafe-sdk](https://pypi.org/project/typesafe-sdk/) | see package | Calls the Jev decision model |
| [Flask](https://flask.palletsprojects.com/) | BSD-3-Clause | HTTP API and static file serving |
| [openai](https://pypi.org/project/openai/) | Apache-2.0 | Any OpenAI-compatible endpoint |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | BSD-3-Clause | Reads the key file |
| [pypdf](https://pypi.org/project/pypdf/) | BSD-3-Clause | Optional `[pdf]` extra, PDF seed upload |
| [camel-ai](https://github.com/camel-ai/camel) | Apache-2.0 | Optional `[oasis]` extra |
| [camel-oasis](https://github.com/camel-ai/oasis) | Apache-2.0 | Optional `[oasis]` extra, the reddit and twitter feeds |
| [Vue](https://vuejs.org/) | MIT | The web app |

## Removed deliberately

**PyMuPDF** was replaced by `pypdf` on 18 September 2026. PyMuPDF is dual licensed,
AGPL-3.0 or a paid Artifex commercial licence, so keeping it meant `jevfish/` carried a
copyleft obligation with nothing to do with MiroFish, and it would have pulled a hosted
interactive demo into AGPL section 13 on its own. `pypdf` is BSD-3-Clause. The swap also
removed 54 MB from the install.

**mcp** was removed on 18 September 2026. It was declared as a runtime dependency with
zero imports anywhere in `src/` or `tests/`.

## Trademarks

Product names are used for identification only. No affiliation with or endorsement by
TypeSafe AI, Google, or the MiroFish authors is claimed. TypeSafe's and Google's logos are
not used anywhere in this project.
