import zipfile
import json
from pathlib import PurePosixPath

# -----------------------------
# Load en_us language file
# -----------------------------
def parse_lang_file(text):
    lang = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            lang[key.strip()] = value.strip()

    return lang


def load_en_us(jar_path):
    with zipfile.ZipFile(jar_path, "r") as jar:
        # Try modern JSON format
        try:
            with jar.open("assets/minecraft/lang/en_us.json") as f:
                return json.load(f)
        except KeyError:
            pass

        # Fallback to legacy .lang format
        with jar.open("assets/minecraft/lang/en_us.lang") as f:
            text = f.read().decode("utf-8", errors="replace")
            return parse_lang_file(text)

# -----------------------------
# Extract only required fields
# -----------------------------
def extract_fields(adv_json, lang):
    result = {}

    display = adv_json.get("display", {})

    # Title
    if "title" in display and "translate" in display["title"]:
        key = display["title"]["translate"]
        result["title"] = lang.get(key, key)

    # Description
    if "description" in display and "translate" in display["description"]:
        key = display["description"]["translate"]
        result["description"] = lang.get(key, key)

    # Icon
    icon = display.get("icon")
    if isinstance(icon, dict):    
        if "id" in icon:
            result["icon"] = icon["id"].split(":")[-1]
        elif "item" in icon:
            result["icon"] = icon["item"].split(":")[-1]

    # Requirements — only keep if multiple
    if "requirements" in adv_json and len(adv_json["requirements"]) > 1:
        result["requirements"] = adv_json["requirements"]
        result["requirements_num"] = len(adv_json["requirements"])
    elif "criteria" in adv_json and len(adv_json["criteria"]) > 1:
        result["requirements"] = [[key] for key in adv_json["criteria"]]
        result["requirements_num"] = len(adv_json["criteria"])

    return result

# -----------------------------
# Build multi-part advancement index
# -----------------------------
def build_multi_part_advancements(jar_path, output_path="index.json"):
    lang = load_en_us(jar_path)

    multi_part_index = {}
    other_index = {}

    with zipfile.ZipFile(jar_path, "r") as jar:
        for name in jar.namelist():
            path = PurePosixPath(name)

            # data/minecraft/(advancement|advancements)/<folder>/<file>.json
            if (
                len(path.parts) >= 5
                and path.parts[0] in ("data", "assets") 
                and path.parts[1] == "minecraft"
                and path.parts[2] in ("advancement", "advancements")
                and path.parts[3] != "recipes"
                and path.suffix == ".json"
            ):
                with jar.open(name) as f:
                    adv_json = json.load(f)

                filtered = extract_fields(adv_json, lang)

                # Build advancement ID WITHOUT caring about singular/plural
                relative_path = PurePosixPath(*path.parts[3:]).with_suffix("")
                key = f"minecraft:{relative_path.as_posix()}"

                # Multi-part vs other
                if "requirements" in filtered:
                    multi_part_index[key] = filtered
                else:
                    other_index[key] = filtered

    # Wrap under "multi_part_advancements"
    final_json = {"multi_part_advancements": multi_part_index, "other_advancements": other_index}

    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(final_json, out, indent=2, ensure_ascii=False)

    print(f"Wrote {len(multi_part_index) + len(other_index)} multi-part advancements to {output_path}")


# -----------------------------
# Run
# -----------------------------
# build_multi_part_advancements("./versions/1.21.11/server-1.21.11.jar")
