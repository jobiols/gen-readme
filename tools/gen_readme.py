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
    fragments = {}
    for fragment_name in FRAGMENTS:
        fragment_filename = os.path.join(
            addon_dir,
            FRAGMENTS_DIR,
            fragment_name + ".rst",
        )
        if os.path.exists(fragment_filename):
            with open(fragment_filename, encoding="utf8") as f:
                fragment = generate_fragment(org_name, repo_name, branch, addon_name, f)
                if fragment:
                    fragments[fragment_name] = fragment
    badges = []
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
                addon_name=addon_name,
                authors=authors,
                badges=badges,
                branch=branch,
                fragments=fragments,
                manifest=manifest,
                org_name=org_name,
                repo_name=repo_name,
                development_status=development_status,
            )
        )
        # Agregar una linea en blanco al final del RST para que no falle el test
        # W7908(missing-newline-extrafiles).
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

    # files = (
    #     ".github/workflows/pre-commit.yml",
    #     ".github/workflows/readme.yml",
    #     ".github/workflows/test.yml",
    #     ".gitignore",
    #     ".pre-commit-config.yaml",
    #     ".pylintrc",
    #     ".pylintrc-mandatory",
    #     ".vscode/settings.json",
    #     "README.md",
    #     "account_delete_payment/README.rst",
    #     "account_delete_payment/__init__.py",
    #     "account_delete_payment/__manifest__.py",
    #     "account_delete_payment/models/__init__.py",
    #     "account_delete_payment/models/account_payment.py",
    #     "account_delete_payment/readme/CONFIGURE.rst",
    #     "account_delete_payment/readme/CONTRIBUTORS.rst",
    #     "account_delete_payment/readme/CREDITS.rst",
    #     "account_delete_payment/readme/DESCRIPTION.rst",
    #     "account_delete_payment/readme/HISTORY.rst",
    #     "account_delete_payment/readme/INSTALL.rst",
    #     "account_delete_payment/readme/ROADMAP.rst",
    #     "account_delete_payment/readme/USAGE.rst",
    #     "account_delete_payment/security/ir.model.access.csv",
    #     "account_delete_payment/static/description/icon.png",
    #     "account_delete_payment/static/description/index.html",
    #     "account_followup_ux/README.rst",
    #     "account_followup_ux/__init__.py",
    #     "account_followup_ux/__manifest__.py",
    #     "account_followup_ux/models/__init__.py",
    #     "account_followup_ux/models/account_move.py",
    #     "account_followup_ux/models/res_partner.py",
    #     "account_followup_ux/readme/CONFIGURE.rst",
    #     "account_followup_ux/readme/CONTRIBUTORS.rst",
    #     "account_followup_ux/readme/CREDITS.rst",
    #     "account_followup_ux/readme/DESCRIPTION.rst",
    #     "account_followup_ux/readme/HISTORY.rst",
    #     "account_followup_ux/readme/INSTALL.rst",
    #     "account_followup_ux/readme/ROADMAP.rst",
    #     "account_followup_ux/readme/USAGE.rst",
    #     "account_followup_ux/static/description/icon.png",
    #     "account_followup_ux/static/description/index.html",
    #     "account_followup_ux/views/account_move_views.xml",
    #     "account_followup_ux/views/followup_view.xml",
    #     "account_followup_ux/views/res_partner_view.xml",
    #     "dependencies.py",
    #     "l10n_py/README.rst",
    #     "l10n_py/__init__.py",
    #     "l10n_py/__manifest__.py",
    #     "l10n_py/data/account.account.template.csv",
    #     "l10n_py/data/account_tax_group.xml",
    #     "l10n_py/data/l10n_latam.identification.type.xml",
    #     "l10n_py/data/l10n_py.xml",
    #     "l10n_py/data/l10n_py_post.xml",
    #     "l10n_py/data/load_account_chart_template.xml",
    #     "l10n_py/data/res.country.state.csv",
    #     "l10n_py/demo/res_company.xml",
    #     "l10n_py/demo/res_partner_demo.xml",
    #     "l10n_py/i18n/es.po",
    #     "l10n_py/migrations/13.0.0.0.0/post-migration-process.py",
    #     "l10n_py/migrations/13.0.0.0.0/pre-migration-rename.py",
    #     "l10n_py/models/__init__.py",
    #     "l10n_py/models/chart_template.py",
    #     "l10n_py/models/l10n_latam_identification_type.py",
    #     "l10n_py/models/partner_type.py",
    #     "l10n_py/models/res_company.py",
    #     "l10n_py/models/res_partner.py",
    #     "l10n_py/readme/CONFIGURE.rst",
    #     "l10n_py/readme/CONTRIBUTORS.rst",
    #     "l10n_py/readme/CREDITS.rst",
    #     "l10n_py/readme/DESCRIPTION.rst",
    #     "l10n_py/readme/HISTORY.rst",
    #     "l10n_py/readme/INSTALL.rst",
    #     "l10n_py/readme/ROADMAP.rst",
    #     "l10n_py/readme/USAGE.rst",
    #     "l10n_py/security/ir.model.access.csv",
    #     "l10n_py/static/description/icon.png",
    #     "l10n_py/static/description/index.html",
    #     "l10n_py/views/res_partner_view.xml",
    #     "l10n_py_autoprinter/README.rst",
    #     "l10n_py_autoprinter/__init__.py",
    #     "l10n_py_autoprinter/__manifest__.py",
    #     "l10n_py_autoprinter/data/receipt_book_data.xml",
    #     "l10n_py_autoprinter/data/report_paperformat.xml",
    #     "l10n_py_autoprinter/demo/partners_demo.xml",
    #     "l10n_py_autoprinter/models/__init__.py",
    #     "l10n_py_autoprinter/models/account_move.py",
    #     "l10n_py_autoprinter/models/account_move_line.py",
    #     "l10n_py_autoprinter/models/account_payment.py",
    #     "l10n_py_autoprinter/models/account_payment_receiptbook.py",
    #     "l10n_py_autoprinter/models/l10n_latam_document_type.py",
    #     "l10n_py_autoprinter/models/res_company.py",
    #     "l10n_py_autoprinter/models/res_partner.py",
    #     "l10n_py_autoprinter/models/stock_picking.py",
    #     "l10n_py_autoprinter/readme/CONFIGURE.rst",
    #     "l10n_py_autoprinter/readme/CONTRIBUTORS.rst",
    #     "l10n_py_autoprinter/readme/CREDITS.rst",
    #     "l10n_py_autoprinter/readme/DESCRIPTION.rst",
    #     "l10n_py_autoprinter/readme/HISTORY.rst",
    #     "l10n_py_autoprinter/readme/INSTALL.rst",
    #     "l10n_py_autoprinter/readme/ROADMAP.rst",
    #     "l10n_py_autoprinter/readme/USAGE.rst",
    #     "l10n_py_autoprinter/security/ir.model.access.csv",
    #     "l10n_py_autoprinter/static/description/icon.png",
    #     "l10n_py_autoprinter/static/description/index.html",
    #     "l10n_py_autoprinter/templates/autoprinter_invoice.xml",
    #     "l10n_py_autoprinter/templates/report_delivery_slip.xml",
    #     "l10n_py_autoprinter/templates/report_invoice.xml",
    #     "l10n_py_autoprinter/templates/report_payment_receipt.xml",
    #     "l10n_py_autoprinter/templates/report_preprinted_invoice.xml",
    #     "l10n_py_autoprinter/tests/__init__.py",
    #     "l10n_py_autoprinter/tests/test_documents.py",
    #     "l10n_py_autoprinter/views/account_payment_receiptbook_view.xml",
    #     "l10n_py_autoprinter/views/account_payment_view.xml",
    #     "l10n_py_autoprinter/views/company_form_view.xml",
    #     "l10n_py_autoprinter/views/invoice_report_action.xml",
    #     "l10n_py_hechauka/README.rst",
    #     "l10n_py_hechauka/__init__.py",
    #     "l10n_py_hechauka/__manifest__.py",
    #     "l10n_py_hechauka/i18n/es_PY.po",
    #     "l10n_py_hechauka/migrations/13.0.1.1/pre-migration.py",
    #     "l10n_py_hechauka/migrations/13.0.1.4.1/post-migration.py",
    #     "l10n_py_hechauka/models/__init__.py",
    #     "l10n_py_hechauka/models/account_move.py",
    #     "l10n_py_hechauka/models/account_move_reversal.py",
    #     "l10n_py_hechauka/models/export_hechauka.py",
    #     "l10n_py_hechauka/readme/CONFIGURE.rst",
    #     "l10n_py_hechauka/readme/CONTRIBUTORS.rst",
    #     "l10n_py_hechauka/readme/CREDITS.rst",
    #     "l10n_py_hechauka/readme/DESCRIPTION.rst",
    #     "l10n_py_hechauka/readme/HISTORY.rst",
    #     "l10n_py_hechauka/readme/INSTALL.rst",
    #     "l10n_py_hechauka/readme/ROADMAP.rst",
    #     "l10n_py_hechauka/readme/USAGE.rst",
    #     "l10n_py_hechauka/security/ir.model.access.csv",
    #     "l10n_py_hechauka/static/description/icon.png",
    #     "l10n_py_hechauka/static/description/index.html",
    #     "l10n_py_hechauka/views/account_move_view.xml",
    #     "l10n_py_hechauka/views/menus_view.xml",
    #     "l10n_py_invoice_document/README.rst",
    #     "l10n_py_invoice_document/__init__.py",
    #     "l10n_py_invoice_document/__manifest__.py",
    #     "l10n_py_invoice_document/data/document_type.xml",
    #     "l10n_py_invoice_document/data/ir_cron_data.xml",
    #     "l10n_py_invoice_document/data/partner_type_data.xml",
    #     "l10n_py_invoice_document/data/payment_terms.xml",
    #     "l10n_py_invoice_document/demo/account_journal_demo.xml",
    #     "l10n_py_invoice_document/demo/account_timbrado_demo.xml",
    #     "l10n_py_invoice_document/i18n/es_PY.po",
    #     "l10n_py_invoice_document/migrations/13.0.0.0.7/post-migration.py",
    #     "l10n_py_invoice_document/migrations/13.0.4.0.0/post-migration.py",
    #     "l10n_py_invoice_document/models/__init__.py",
    #     "l10n_py_invoice_document/models/account_journal.py",
    #     "l10n_py_invoice_document/models/account_move.py",
    #     "l10n_py_invoice_document/models/account_move_line.py",
    #     "l10n_py_invoice_document/models/account_move_reversal.py",
    #     "l10n_py_invoice_document/models/l10n_latam_document_type.py",
    #     "l10n_py_invoice_document/models/product_category.py",
    #     "l10n_py_invoice_document/models/product_template.py",
    #     "l10n_py_invoice_document/models/res_partner.py",
    #     "l10n_py_invoice_document/models/timbrado.py",
    #     "l10n_py_invoice_document/readme/CONFIGURE.rst",
    #     "l10n_py_invoice_document/readme/CONTRIBUTORS.rst",
    #     "l10n_py_invoice_document/readme/CREDITS.rst",
    #     "l10n_py_invoice_document/readme/DESCRIPTION.rst",
    #     "l10n_py_invoice_document/readme/HISTORY.rst",
    #     "l10n_py_invoice_document/readme/INSTALL.rst",
    #     "l10n_py_invoice_document/readme/ROADMAP.rst",
    #     "l10n_py_invoice_document/readme/USAGE.rst",
    #     "l10n_py_invoice_document/security/ir.model.access.csv",
    #     "l10n_py_invoice_document/static/description/icon.png",
    #     "l10n_py_invoice_document/static/description/index.html",
    #     "l10n_py_invoice_document/tests/__init__.py",
    #     "l10n_py_invoice_document/tests/common.py",
    #     "l10n_py_invoice_document/tests/test_invoice.py",
    #     "l10n_py_invoice_document/tests/test_stamp.py",
    #     "l10n_py_invoice_document/views/account_journal_view.xml",
    #     "l10n_py_invoice_document/views/account_move_view.xml",
    #     "l10n_py_invoice_document/views/l10n_latam_document_type_view.xml",
    #     "l10n_py_invoice_document/views/partner_type_view.xml",
    #     "l10n_py_invoice_document/views/product_category_view.xml",
    #     "l10n_py_invoice_document/views/product_template_view.xml",
    #     "l10n_py_invoice_document/views/timbrado_views.xml",
    #     "l10n_py_padron_ruc/README.rst",
    #     "l10n_py_padron_ruc/__init__.py",
    #     "l10n_py_padron_ruc/__manifest__.py",
    #     "l10n_py_padron_ruc/data/actions_server.xml",
    #     "l10n_py_padron_ruc/models/__init__.py",
    #     "l10n_py_padron_ruc/models/res_partner.py",
    #     "l10n_py_padron_ruc/models/sat_ruc_padron.py",
    #     "l10n_py_padron_ruc/readme/CONFIGURE.rst",
    #     "l10n_py_padron_ruc/readme/CONTRIBUTORS.rst",
    #     "l10n_py_padron_ruc/readme/CREDITS.rst",
    #     "l10n_py_padron_ruc/readme/DESCRIPTION.rst",
    #     "l10n_py_padron_ruc/readme/HISTORY.rst",
    #     "l10n_py_padron_ruc/readme/INSTALL.rst",
    #     "l10n_py_padron_ruc/readme/ROADMAP.rst",
    #     "l10n_py_padron_ruc/readme/USAGE.rst",
    #     "l10n_py_padron_ruc/security/ir.model.access.csv",
    #     "l10n_py_padron_ruc/static/description/icon.png",
    #     "l10n_py_padron_ruc/static/description/index.html",
    #     "l10n_py_padron_ruc/tests/__init__.py",
    #     "l10n_py_padron_ruc/tests/common.py",
    #     "l10n_py_padron_ruc/tests/test_calc_dv.py",
    #     "l10n_py_padron_ruc/tests/test_duplicar_vat.py",
    #     "l10n_py_padron_ruc/views/res_partner_views.xml",
    #     "l10n_py_padron_ruc/wizards/__init__.py",
    #     "l10n_py_padron_ruc/wizards/import_padron.py",
    #     "l10n_py_padron_ruc/wizards/import_padron_view.xml",
    #     "l10n_py_pos/README.rst",
    #     "l10n_py_pos/__init__.py",
    #     "l10n_py_pos/__manifest__.py",
    #     "l10n_py_pos/models/__init__.py",
    #     "l10n_py_pos/models/pos_config.py",
    #     "l10n_py_pos/models/pos_order.py",
    #     "l10n_py_pos/readme/CONFIGURE.rst",
    #     "l10n_py_pos/readme/CONTRIBUTORS.rst",
    #     "l10n_py_pos/readme/CREDITS.rst",
    #     "l10n_py_pos/readme/DESCRIPTION.rst",
    #     "l10n_py_pos/readme/HISTORY.rst",
    #     "l10n_py_pos/readme/INSTALL.rst",
    #     "l10n_py_pos/readme/ROADMAP.rst",
    #     "l10n_py_pos/readme/USAGE.rst",
    #     "l10n_py_pos/static/description/icon.png",
    #     "l10n_py_pos/static/description/index.html",
    #     "l10n_py_pos/static/src/js/description/icon.jpg",
    #     "l10n_py_pos/static/src/js/l10n_py_pos.js",
    #     "l10n_py_pos/views/point_of_sale_report.xml",
    #     "l10n_py_pos/views/pos_assets.xml",
    #     "l10n_py_pos/views/pos_config_view.xml",
    #     "l10n_py_vat_book/README.rst",
    #     "l10n_py_vat_book/__init__.py",
    #     "l10n_py_vat_book/__manifest__.py",
    #     "l10n_py_vat_book/data/account_financial_report_data.xml",
    #     "l10n_py_vat_book/models/__init__.py",
    #     "l10n_py_vat_book/models/account_move.py",
    #     "l10n_py_vat_book/models/l10n_py_vat_book.py",
    #     "l10n_py_vat_book/readme/CONFIGURE.rst",
    #     "l10n_py_vat_book/readme/CONTRIBUTORS.rst",
    #     "l10n_py_vat_book/readme/CREDITS.rst",
    #     "l10n_py_vat_book/readme/DESCRIPTION.rst",
    #     "l10n_py_vat_book/readme/HISTORY.rst",
    #     "l10n_py_vat_book/readme/INSTALL.rst",
    #     "l10n_py_vat_book/readme/ROADMAP.rst",
    #     "l10n_py_vat_book/readme/USAGE.rst",
    #     "l10n_py_vat_book/report/__init__.py",
    #     "l10n_py_vat_book/report/account_py_vat_line.py",
    #     "l10n_py_vat_book/report/account_py_vat_line_views.xml",
    #     "l10n_py_vat_book/security/ir.model.access.csv",
    #     "l10n_py_vat_book/security/security.xml",
    #     "l10n_py_vat_book/static/description/icon.png",
    #     "l10n_py_vat_book/static/description/index.html",
    #     "l10n_py_vat_book/tests/__init__.py",
    #     "l10n_py_vat_book/tests/common.py",
    #     "l10n_py_vat_book/tests/test_vat_base.py",
    #     "make_readme.sh",
    #     "requirements.txt",
    #     "run_tests.sh",
    #     "valued_loss/README.rst",
    #     "valued_loss/__init__.py",
    #     "valued_loss/__manifest__.py",
    #     "valued_loss/models/__init__.py",
    #     "valued_loss/models/valued_loss_pivot_view.py",
    #     "valued_loss/readme/CONFIGURE.rst",
    #     "valued_loss/readme/CONTRIBUTORS.rst",
    #     "valued_loss/readme/CREDITS.rst",
    #     "valued_loss/readme/DESCRIPTION.rst",
    #     "valued_loss/readme/HISTORY.rst",
    #     "valued_loss/readme/INSTALL.rst",
    #     "valued_loss/readme/ROADMAP.rst",
    #     "valued_loss/readme/USAGE.rst",
    #     "valued_loss/security/ir.model.access.csv",
    #     "valued_loss/static/description/icon.png",
    #     "valued_loss/static/description/index.html",
    #     "valued_loss/views/menu_views.xml",
    #     "valued_loss/views/valued_loss_pivot_view.xml",
    # )

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
            if not "readme" in modules[module]:
                bad_modules.append(module)

        for module in bad_modules:
            print(f"There is no readme in {module}")

        if bad_modules:
            exit(1)
        exit(0)

    addons = list()
    if addons_dir:
        addons.extend(find_addons(addons_dir))
    readme_filenames = []
    for addon_name, addon_dir, manifest in addons:
        if not os.path.exists(
            os.path.join(addon_dir, FRAGMENTS_DIR, "DESCRIPTION.rst")
        ):
            continue
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
