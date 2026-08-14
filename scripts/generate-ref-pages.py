"""Generate the code reference pages and navigation."""

import importlib
import inspect
from pathlib import Path

import mkdocs_gen_files

from derive_py.cli._tree import command_tree

REPO_ROOT = Path(__file__).parent.parent
PACKAGE_DIR = REPO_ROOT / "derive_py"


def get_public_members(module_path: str, class_name: str) -> list[str]:
    """Extract all public (non-private) members from a class.

    Args:
        module_path: Full module path, e.g., "derive_py._clients.rest.http.orders"
        class_name: Class name, e.g., "OrderOperations"

    Returns:
        List of public member names
    """

    # Import the module and get the class
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    # Get all members, filter out private ones
    public_members = [name for name, _ in inspect.getmembers(cls) if not name.startswith('_') or name in ('__init__',)]

    return public_members


def get_classes_defined_in(module_path: str) -> list[str]:
    """Get classes actually defined in this module."""

    module = importlib.import_module(module_path)
    classes = [
        (name, obj) for name, obj in inspect.getmembers(module, inspect.isclass) if obj.__module__ == module_path
    ]
    classes.sort(key=lambda pair: inspect.getsourcelines(pair[1])[1])
    return [name for name, _ in classes]


def generate_client_docs(nav: mkdocs_gen_files.Nav):
    """Generate docs for HTTP/Async clients - show public interface only."""

    clients = {
        "HTTPClient": "derive_py._clients.rest.http.client",
        "AsyncHTTPClient": "derive_py._clients.rest.async_http.client",
    }

    for display_name, module_path in clients.items():
        doc_path = Path("clients", f"{display_name.lower()}.md")
        full_doc_path = Path("reference", doc_path)

        nav[("Clients", display_name)] = doc_path.as_posix()
        public_members = get_public_members(module_path, display_name)

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            fd.write(f"# {display_name}\n\n")
            fd.write(f"::: {module_path}.{display_name}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: false\n")
            fd.write("      heading_level: 2\n")
            fd.write("      members_order: source\n")
            fd.write(f"      members: {public_members}\n")
            fd.write("      show_bases: false\n")
            fd.write("      show_source: false\n")
            fd.write("      inherited_members: false\n")
            fd.write("      show_signature_annotations: true\n")


def generate_account_docs(nav: mkdocs_gen_files.Nav):
    """Generate docs for account classes - show public methods only."""

    accounts = {
        "LightAccount": "derive_py._clients.rest.http.account",
        "Subaccount": "derive_py._clients.rest.http.subaccount",
    }

    for display_name, module_path in accounts.items():
        doc_path = Path("accounts", f"{display_name.lower()}.md")
        full_doc_path = Path("reference", doc_path)

        nav[("Accounts", display_name)] = doc_path.as_posix()
        public_members = get_public_members(module_path, display_name)

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            fd.write(f"# {display_name}\n\n")
            fd.write(f"::: {module_path}.{display_name}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: false\n")
            fd.write("      heading_level: 2\n")
            fd.write("      members_order: source\n")
            fd.write(f"      members: {public_members}\n")
            fd.write("      show_bases: false\n")
            fd.write("      show_source: false\n")
            fd.write("      inherited_members: false\n")
            fd.write("      show_signature_annotations: true\n")


def generate_operation_docs(nav: mkdocs_gen_files.Nav):
    """Generate docs for operation classes - show all public methods."""

    operations = {
        "CollateralOperations": "derive_py._clients.rest.http.collateral",
        "HistoryOperations": "derive_py._clients.rest.http.history",
        "MarketOperations": "derive_py._clients.rest.http.markets",
        "MMPOperations": "derive_py._clients.rest.http.mmp",
        "OrderOperations": "derive_py._clients.rest.http.orders",
        "PositionOperations": "derive_py._clients.rest.http.positions",
        "RFQOperations": "derive_py._clients.rest.http.rfq",
        "SystemOperations": "derive_py._clients.rest.http.system",
        "VaultOperations": "derive_py._clients.rest.http.vaults",
    }

    for display_name, module_path in operations.items():
        doc_path = Path("operations", f"{display_name.lower()}.md")
        full_doc_path = Path("reference", doc_path)

        nav[("Operations", display_name)] = doc_path.as_posix()
        public_members = get_public_members(module_path, display_name)

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            fd.write(f"# {display_name}\n\n")
            fd.write("!!! info\n")
            fd.write(f"    Access via `client.{display_name.lower().replace('operations', '')}` property.\n\n")
            fd.write(f"::: {module_path}.{display_name}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: false\n")
            fd.write("      heading_level: 2\n")
            fd.write("      members_order: source\n")
            fd.write(f"      members: {public_members}\n")
            fd.write("      show_bases: false\n")
            fd.write("      show_source: false\n")
            fd.write("      inherited_members: false\n")


def generate_datatype_docs(nav: mkdocs_gen_files.Nav):
    """Generate docs for data types with specialized settings per type."""

    # Enums - show all members
    enums_parent_path = Path("reference", "data_types", "enums.md")
    nav[("Data Types", "Enums")] = Path("data_types", "enums.md").as_posix()

    enums = get_classes_defined_in("derive_py.data_types.enums")

    with mkdocs_gen_files.open(enums_parent_path, "w") as fd:
        fd.write("# Enums\n\n")
        fd.write("This section contains all enumeration types used in the derive_py.\n\n")
        fd.write("## Available Enums\n\n")
        for enum in enums:
            fd.write(f"- [{enum}](enums/{enum.lower()}.md)\n")

    for enum_name in enums:
        full_doc_path = Path("reference", "data_types", "enums", f"{enum_name.lower()}.md")
        nav[("Data Types", "Enums", enum_name)] = Path("data_types", "enums", f"{enum_name.lower()}.md").as_posix()

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            fd.write(f"# {enum_name}\n\n")
            fd.write(f"::: derive_py.data_types.enums.{enum_name}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: false\n")
            fd.write("      heading_level: 2\n")
            fd.write("      show_source: true\n")
            fd.write("      members: true\n")

    # Models - show all fields and methods
    models_parent_path = Path("data_types", "models.md")
    full_models_parent_path = Path("reference", models_parent_path)
    nav[("Data Types", "Models")] = models_parent_path.as_posix()

    models = get_classes_defined_in("derive_py.data_types.models")

    with mkdocs_gen_files.open(full_models_parent_path, "w") as fd:
        fd.write("# Models\n\n")
        fd.write("This section contains all data model classes used in the derive_py.\n\n")
        fd.write("## Available Models\n\n")
        for model in models:
            fd.write(f"- [{model}](models/{model.lower()}.md)\n")

    for model_name in models:
        doc_path = Path("data_types", "models", f"{model_name.lower()}.md")
        full_doc_path = Path("reference", doc_path)
        nav[("Data Types", "Models", model_name)] = doc_path.as_posix()

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            fd.write(f"# {model_name}\n\n")
            fd.write(f"::: derive_py.data_types.models.{model_name}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: false\n")
            fd.write("      heading_level: 2\n")
            fd.write("      show_source: true\n")
            fd.write("      members: true\n")


def generate_exceptions_docs(nav: mkdocs_gen_files.Nav):
    doc_path = Path("exceptions.md")
    full_doc_path = Path("reference", doc_path)
    nav[("Exceptions",)] = doc_path.as_posix()

    exceptions = get_classes_defined_in("derive_py.exceptions")

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write("# Exceptions\n\n")

        for exc_name in exceptions:
            fd.write(f"## {exc_name}\n\n")
            fd.write(f"::: derive_py.exceptions.{exc_name}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: false\n")
            fd.write("      heading_level: 3\n")
            fd.write("      show_bases: true\n")
            fd.write("      show_source: true\n")
            fd.write("      members: false\n\n")


def generate_cli_docs(nav: mkdocs_gen_files.Nav):
    """Generate CLI documentation."""
    from derive_py.cli import cli  # or wherever your Click group lives

    cli_path = Path("cli.md")

    with mkdocs_gen_files.open(cli_path, "w") as fd:
        fd.write("# CLI Reference\n\n")
        fd.write("The `drv` command-line tool provides access to Derive functionality from your terminal.\n\n")

        fd.write("## Getting Help\n\n")
        fd.write("Run any command with `--help` to see detailed usage:\n\n")
        fd.write("```bash\n")
        fd.write("drv --help              # Show all commands\n")
        fd.write("```\n\n")

        fd.write("## Command Tree\n\n")
        fd.write("```\n")
        for line in command_tree(cli, verbose=True, use_rich=False):
            fd.write(line + "\n")
        fd.write("```\n\n")

        fd.write("## Demo\n\n")
        fd.write("![CLI Demo](cli_demo.gif)\n\n")


def build_nav_and_files():
    """Build complete navigation and documentation files."""
    nav = mkdocs_gen_files.Nav()

    # Generate each section with appropriate settings
    generate_client_docs(nav)
    generate_account_docs(nav)
    generate_operation_docs(nav)
    generate_datatype_docs(nav)
    generate_exceptions_docs(nav)
    generate_cli_docs(nav)

    # Write navigation
    with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
        nav_file.writelines(nav.build_literate_nav())


if __name__ == "__main__":
    build_nav_and_files()
