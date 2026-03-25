"""
Inject Colab Bootstrap cell into all OmniCare notebooks.
"""

import json
import os

NOTEBOOKS_DIR = os.path.dirname(os.path.abspath(__file__))

BOOTSTRAP_MARKDOWN_CELL = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 0. Colab Bootstrap (run this first)\n",
        "\n",
        "Auto-detects environment. In Colab, clones the private repo using your GitHub PAT.\n",
        "\n",
        "**One-time setup:** In Colab, go to the **Key icon** in the left sidebar > Add a secret named `GITHUB_PAT` with your [GitHub Personal Access Token](https://github.com/settings/tokens)."
    ]
}

BOOTSTRAP_CODE_CELL = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# ===========================================================\n",
        "# Colab Bootstrap - run this cell first (works locally too)\n",
        "# ===========================================================\n",
        "import os, sys\n",
        "\n",
        "try:\n",
        "    from google.colab import userdata\n",
        "    IN_COLAB = True\n",
        "except ImportError:\n",
        "    IN_COLAB = False\n",
        "\n",
        "REPO_DIR = '/content/omnicare-clinical-copilot'\n",
        "\n",
        "if IN_COLAB:\n",
        "    if not os.path.exists(REPO_DIR):\n",
        "        token = userdata.get('GITHUB_PAT')\n",
        "        repo_url = f'https://{token}@github.com/Yashground/omnicare-clinical-copilot.git'\n",
        "        os.system(f'git clone {repo_url} {REPO_DIR}')\n",
        "    NOTEBOOKS_DIR = os.path.join(REPO_DIR, 'notebooks')\n",
        "    os.makedirs('/content/encounters', exist_ok=True)\n",
        "    os.makedirs('/content/sample_data', exist_ok=True)\n",
        "else:\n",
        "    NOTEBOOKS_DIR = os.path.dirname(os.path.abspath('__file__'))\n",
        "\n",
        "if NOTEBOOKS_DIR not in sys.path:\n",
        "    sys.path.insert(0, NOTEBOOKS_DIR)\n",
        "\n",
        "print(f'Environment ready | Colab: {IN_COLAB} | Notebooks dir: {NOTEBOOKS_DIR}')"
    ]
}

OLD_PATH_LINES_STRIPPED = [
    "sys.path.insert(0, os.path.dirname(os.path.abspath(\"__file__\")))",
    "# Add utils to path",
]

NOTEBOOKS = [
    "00_setup_and_models.ipynb",
    "01_consultation_audio_soap.ipynb",
    "02_admission_vitals_fhir.ipynb",
    "03_radiology_dicom_imaging.ipynb",
    "04_discharge_summary.ipynb",
]


def has_bootstrap(cells):
    for cell in cells:
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if "Colab Bootstrap" in source:
                return True
    return False


def remove_old_path_hack(cells):
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        new_source = []
        for line in cell.get("source", []):
            if line.strip() in OLD_PATH_LINES_STRIPPED:
                continue
            # Also skip blank lines that immediately followed the removed lines
            new_source.append(line)
        cell["source"] = new_source


def remove_section8_encounter_dir(cells):
    i = 0
    while i < len(cells):
        cell = cells[i]
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if "Create Encounter State Directory" in source:
                cells.pop(i)
                if i < len(cells) and cells[i].get("cell_type") == "code":
                    code_source = "".join(cells[i].get("source", []))
                    if "/content/encounters" in code_source:
                        cells.pop(i)
                break
        i += 1


def inject_notebook(notebook_path):
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb["cells"]

    if has_bootstrap(cells):
        print(f"  SKIP (already has bootstrap): {os.path.basename(notebook_path)}")
        return False

    remove_old_path_hack(cells)

    if "00_setup" in notebook_path:
        remove_section8_encounter_dir(cells)

    insert_idx = 1
    for i, cell in enumerate(cells):
        if cell.get("cell_type") == "markdown":
            insert_idx = i + 1
            break

    cells.insert(insert_idx, BOOTSTRAP_MARKDOWN_CELL)
    cells.insert(insert_idx + 1, BOOTSTRAP_CODE_CELL)

    nb["cells"] = cells

    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=True)

    print(f"  DONE: {os.path.basename(notebook_path)}")
    return True


def main():
    print("Injecting Colab Bootstrap into OmniCare notebooks...\n")
    modified = 0
    for nb_name in NOTEBOOKS:
        nb_path = os.path.join(NOTEBOOKS_DIR, nb_name)
        if not os.path.exists(nb_path):
            print(f"  NOT FOUND: {nb_name}")
            continue
        if inject_notebook(nb_path):
            modified += 1

    print(f"\nModified {modified}/{len(NOTEBOOKS)} notebooks.")
    print(f"\nNext steps:")
    print(f"  1. In Colab, add a secret: Key icon > GITHUB_PAT > your token")
    print(f"  2. git add . && git commit -m 'Add Colab bootstrap' && git push")
    print(f"  3. Open from Colab: File > Open > GitHub > Yashground/omnicare-clinical-copilot")


if __name__ == "__main__":
    main()
