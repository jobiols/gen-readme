import click
import os
import re
from .manifest import find_addons
from jinja2 import Template
from docutils.core import publish_file
import tempfile

FRAGMENTS_DIR = "readme"

FRAGMENTS = (
    "DESCRIPTION",
    "INSTALL",
    "CONFIGURE",
    "USAGE",
    "ROADMAP",
    "DEVELOP",
    "CONTRIBUTORS",
    "CREDITS",
    "HISTORY",
)

DEVELOPMENT_STATUS_BADGES = {
    "mature": (
        "https://img.shields.io/badge/maturity-Mature-brightgreen.png",
        "https://odoo-community.org/page/development-status",
        "Mature",
    ),
    "production/stable": (
        "https://img.shields.io/badge/maturity-Production%2FStable-green.png",
        "https://odoo-community.org/page/development-status",
        "Production/Stable",
    ),
    "beta": (
        "https://img.shields.io/badge/maturity-Beta-yellow.png",
        "https://odoo-community.org/page/development-status",
        "Beta",
    ),
    "alpha": (
        "https://img.shields.io/badge/maturity-Alpha-red.png",
        "https://odoo-community.org/page/development-status",
        "Alpha",
    ),
}

LICENSE_BADGES = {
    "AGPL-3": (
        "https://img.shields.io/badge/licence-AGPL--3-blue.png",
        "http://www.gnu.org/licenses/agpl-3.0-standalone.html",
        "License: AGPL-3",
    ),
    "LGPL-3": (
        "https://img.shields.io/badge/licence-LGPL--3-blue.png",
        "http://www.gnu.org/licenses/lgpl-3.0-standalone.html",
        "License: LGPL-3",
    ),
    "GPL-3": (
        "https://img.shields.io/badge/licence-GPL--3-blue.png",
        "http://www.gnu.org/licenses/gpl-3.0-standalone.html",
        "License: GPL-3",
    ),
}

# this comes from pypa/readme_renderer
RST2HTML_SETTINGS = {
    # Prevent local files from being included into the rendered output.
    # This is a security concern because people can insert files
    # that are part of the system, such as /etc/passwd.
    "file_insertion_enabled": False,
    # Halt rendering and throw an exception if there was any errors or
    # warnings from docutils.
    "halt_level": 2,
    # Output math blocks as LaTeX that can be interpreted by MathJax for
    # a prettier display of Math formulas.
    "math_output": "MathJax",
    # Disable raw html as enabling it is a security risk, we do not want
    # people to be able to include any old HTML in the final output.
    "raw_enabled": False,
    # Use typographic quotes, and transform --, ---, and ... into their
    # typographic counterparts.
    "smart_quotes": True,
    # Use the short form of syntax highlighting so that the generated
    # Pygments CSS can be used to style the output.
    "syntax_highlight": "short",
}


def gen_one_addon_index(readme_filename):
    addon_dir = os.path.dirname(readme_filename)
    index_dir = os.path.join(addon_dir, "static", "description")
    index_filename = os.path.join(index_dir, "index.html")
    if os.path.exists(index_filename):
        with open(index_filename) as f:
            if "oca-gen-addon-readme" not in f.read():
                # index was created manually
                return
    if not os.path.isdir(index_dir):
        os.makedirs(index_dir)
    publish_file(
        source_path=readme_filename,
        destination_path=index_filename,
        writer_name="html4css1",
        settings_overrides=RST2HTML_SETTINGS,
    )
    with open(index_filename, "rb") as f:
        index = f.read()
    # remove the docutils version from generated html, to avoid
    # useless changes in the readme
    index = re.sub(
        rb"(<meta.*generator.*Docutils)\s*[\d.]+", rb"\1", index, re.MULTILINE
    )
    with open(index_filename, "wb") as f:
        f.write(index)
    return index_filename


def check_rst(readme_filename):
    with tempfile.NamedTemporaryFile() as f:
        publish_file(
            source_path=readme_filename,
            destination=f,
            writer_name="html4css1",
            settings_overrides=RST2HTML_SETTINGS,
        )


def make_repo_badge(org_name, repo_name, branch, addon_name):
    badge_repo_name = repo_name.replace("-", "--")
    return (
        "https://img.shields.io/badge/github-{org_name}%2F{badge_repo_name}"
        "-lightgray.png?logo=github".format(**locals()),
        "https://github.com/{org_name}/{repo_name}/tree/"
        "{branch}/{addon_name}".format(**locals()),
        "{org_name}/{repo_name}".format(**locals()),
    )


def generate_fragment(org_name, repo_name, branch, addon_name, file):
    fragment_lines = file.readlines()
    if not fragment_lines:
        return False

    # Replace relative path by absolute path for figures
    image_path_re = re.compile(r".*\s*\.\..* (figure|image)::\s+(?P<path>.*?)\s*$")
    module_url = (
        "https://raw.githubusercontent.com/{org_name}/{repo_name}"
        "/{branch}/{addon_name}/".format(**locals())
    )
    for index, fragment_line in enumerate(fragment_lines):
        mo = image_path_re.match(fragment_line)
        if not mo:
            continue
        path = mo.group("path")

        if path.startswith("http"):
            # It is already an absolute path
            continue
        else:
            # remove '../' if exists that make the fragment working
            # on github interface, in the 'readme' subfolder
            relative_path = path.replace("../", "")
            fragment_lines[index] = fragment_line.replace(
                path, urljoin(module_url, relative_path)
            )
    fragment = "".join(fragment_lines)

    # ensure that there is a new empty line at the end of the fragment
    if fragment[-1] != "\n":
        fragment += "\n"
    return fragment


def gen_one_addon_readme(org_name, repo_name, branch, addon_name, addon_dir, manifest):
    fragments = dict()
    readme_characters = 0
    for fragment_name in FRAGMENTS:
        fragment_filename = os.path.join(
            addon_dir,
            FRAGMENTS_DIR,
            fragment_name + ".rst",
        )
        # si el fragmento no existe lo creamos vacio
        if not os.path.exists(fragment_filename):
            with open(fragment_filename, "w") as f:
                pass
        # si el fragmento existe lo leemos
        if os.path.exists(fragment_filename):
            with open(fragment_filename, encoding="utf8") as f:
                fragment = generate_fragment(org_name, repo_name, branch, addon_name, f)
                # para medir que tan grande es el readme, y poner o no el TOC
                readme_characters += 0 if not fragment else len(fragment)
                if fragment:
                    fragments[fragment_name] = fragment
    badges = list()
    development_status = manifest.get("development_status", "Beta").lower()
    if development_status in DEVELOPMENT_STATUS_BADGES:
        badges.append(DEVELOPMENT_STATUS_BADGES[development_status])
    license = manifest.get("license")
    if license in LICENSE_BADGES:
        badges.append(LICENSE_BADGES[license])
    badges.append(make_repo_badge(org_name, repo_name, branch, addon_name))
    authors = [
        a.strip()
        for a in manifest.get("author", "").split(",")
        if "(OCA)" not in a
        # remove OCA because it's in authors for the purpose
        # of finding OCA addons in apps.odoo.com, OCA is not
        # a real author, but is rather referenced in the
        # maintainers section
    ]
    # generate
    template_filename = os.path.join(
        os.path.dirname(__file__), "gen_addon_readme.template"
    )
    readme_filename = os.path.join(addon_dir, "README.rst")
    with open(template_filename, encoding="utf8") as tf:
        template = Template(tf.read())
    with open(readme_filename, "w", encoding="utf8") as rf:
        rf.write(
            template.render(
                {
                    "addon_name": addon_name,
                    "authors": authors,
                    "badges": badges,
                    "branch": branch,
                    "fragments": fragments,
                    "manifest": manifest,
                    "org_name": org_name,
                    "repo_name": repo_name,
                    "development_status": development_status,
                    "toc": readme_characters > 1000,
                }
            )
        )
        rf.write("\n")
    return readme_filename


@click.command()
@click.argument(
    "files",
    type=click.Path(exists=False),
    nargs=-1,
)
@click.option(
    "--org-name",
    help="Organization name",
)
@click.option(
    "--repo-name",
    help="Repository name, eg. server-tools.",
)
@click.option(
    "--branch",
    help="Odoo series. eg 11.0.",
)
@click.option(
    "--addons-dir",
    type=click.Path(dir_okay=True, file_okay=False, exists=False),
    help="Directory containing several addons, the README will be "
    "generated for all installable addons found there...",
)
@click.option(
    "--gen-html/--no-gen-html",
    default=True,
    help="Generate index html file.",
)
def gen_readme(files, org_name, repo_name, branch, addons_dir, gen_html):
    """main function"""

    if files:
        # si vienen files es porque lo llamam del pre-commit
        modules = dict()
        # armar diccionario con los modulos y los archivos / directorios de primer nivel
        for file in files:
            if file.startswith(".") or len(file.split("/")) == 1:
                continue
            module = file.split("/")[0]
            if not module in modules:
                modules[module] = [file.split("/")[1]]
            else:
                modules[module].append(file.split("/")[1])

        bad_modules = list()

        # verificar que en todos los modulos existe readme
        for module in modules:
            file_list = modules[module]
            if not "readme" in file_list and "__manifest__" in file_list:
                bad_modules.append(module)

        for module in bad_modules:
            print(f"There is no readme in {module}")

        if bad_modules:
            exit(1)
        exit(0)

    addons = list()
    if addons_dir:
        # obtiene lista de diccionarios con los datos relevantes de cada modulo.
        addons.extend(find_addons(addons_dir))

    readme_filenames = list()
    for addon_name, addon_dir, manifest in addons:
        # si no existe el readme (directorio) lo creamos
        if not os.path.exists(os.path.join(addon_dir, FRAGMENTS_DIR)):
            os.mkdir(os.path.join(addon_dir, FRAGMENTS_DIR))

        readme_filename = gen_one_addon_readme(
            org_name, repo_name, branch, addon_name, addon_dir, manifest
        )
        check_rst(readme_filename)
        readme_filenames.append(readme_filename)
        if gen_html:
            if not manifest.get("preloadable", True):
                continue
            index_filename = gen_one_addon_index(readme_filename)
            if index_filename:
                readme_filenames.append(index_filename)
