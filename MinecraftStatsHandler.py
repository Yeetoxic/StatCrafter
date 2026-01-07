import os
import requests
import json

username_map = {}

class MinecraftStatsHandler:
    def __init__(self, uuid):
        self.uuid = uuid
        self.username = "notch"  # Default value
        self.folder = self.get_playerdata_folder()
        self.MojangAPI_URL = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
        self.skins_folder = "./static/skins"
        self.capes_folder = "./static/capes"
        os.makedirs(self.skins_folder, exist_ok=True)
        os.makedirs(self.capes_folder, exist_ok=True)


    def get_playerdata_folder(self):
        """
        Reads the 'playerdata' folder and returns a list of UUIDs from the file names.
        Assumes file names are formatted as <UUID>.dat.
        """
        # Correct path based on the new file system
        folder_path = "../world/playerdata"
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")
        result = []
        for file in os.listdir(folder_path):
            if file.endswith(".dat"):
                result.append(file.split(".")[0])
        #print(result)
        return result


    def get_minecraft_usernames(self):
        try:
            response = requests.get(self.MojangAPI_URL)
            if response.status_code == 200:
                data = response.json()
                self.username = data['name']
                username_map[self.uuid] = self.username
                return data
            elif response.status_code == 204:
                #"UUID not found, possible offline mode enabled"
                data = {
                    "id" : "069a79f444e94726a5befca90e38aaf5",
                    "name" : "Unknown account (offline)",
                    "properties" : [ {
                        "name" : "textures",
                        "value" : "ewogICJ0aW1lc3RhbXAiIDogMTc2NzczNzY1OTQxMiwKICAicHJvZmlsZUlkIiA6ICI3M2YzN2M2OWFjZmM0NDMyODc1YTk3ZmEzM2UwYmU5MCIsCiAgInByb2ZpbGVOYW1lIiA6ICJPbHBlcyIsCiAgInRleHR1cmVzIiA6IHsKICAgICJTS0lOIiA6IHsKICAgICAgInVybCIgOiAiaHR0cDovL3RleHR1cmVzLm1pbmVjcmFmdC5uZXQvdGV4dHVyZS84Yzg3ZDRhY2QxMTFiY2ZkMmZjNDdmMmRhZmYzZjg0Njk2MjE4ZTNkMTcyZDgzYjZiYjZhYTRiMmRmMzUwODMyIgogICAgfSwKICAgICJDQVBFIiA6IHsKICAgICAgInVybCIgOiAiaHR0cDovL3RleHR1cmVzLm1pbmVjcmFmdC5uZXQvdGV4dHVyZS81ZWM5MzBjZGQyNjI5Yzg3NzE2NTVjNjBlZWJlYjg2N2I0YjY1NTliMGU2ZDNiYzcxYzQwYzk2MzQ3ZmEwM2YwIgogICAgfQogIH0KfQ=="
                    } ],
                    "profileActions" : [ ]
                } 
                self.username = data['name']
                username_map[self.uuid] = self.username
                return data 
            elif response.status_code == 404:
                return "Error: UUID not found. Check if the UUID is correct."
            # elif response.status_code == 204:
            #     return "No content found. The UUID might not exist."
            else:
                return f"Error: {response.status_code} - {response.reason}"
        except requests.exceptions.RequestException as e:
            return f"An error occurred while fetching usernames: {e}"


    def get_minecraft_skins(self):
        try:
            head_url = f"https://mineskin.eu/helm/{self.username}/100.png"
            skin_url = f"https://mineskin.eu/skin/{self.username}"

            # Download and save head skin
            head_response = requests.get(head_url)
            if head_response.status_code == 200:
                head_file = os.path.join(self.skins_folder, f"{self.uuid}_head.png")
                with open(head_file, "wb") as file:
                    file.write(head_response.content)
                #print(f"Head image successfully saved as {head_file}")
            else:
                print(f"Error fetching head skin: {head_response.status_code} - {head_response.reason}")

            # Download and save full skin
            skin_response = requests.get(skin_url)
            if skin_response.status_code == 200:
                skin_file = os.path.join(self.skins_folder, f"{self.uuid}.png")
                with open(skin_file, "wb") as file:
                    file.write(skin_response.content)
                #print(f"Skin image successfully saved as {skin_file}")
            else:
                print(f"Error fetching full skin: {skin_response.status_code} - {skin_response.reason}")

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching skins: {e}")

    
    def get_minecraft_capes(self):
        try:
            user_url = f"https://api.capes.dev/load/{self.uuid}/minecraft"

            # Get the user's cape url
            cape_response = requests.get(user_url)
            if cape_response.status_code == 200:
                data = cape_response.json()
                if data['exists']:
                    cape_url = data['imageUrl']
                else:
                    return f'No cape found for {self.username}!'
            else:
                print(f"Error fetching cape: {cape_response.status_code} - {cape_response.reason}")


            # Download and save cape
            if not cape_url:
                return "no cape url"
            cape_response = requests.get(cape_url)
            if cape_response.status_code == 200:
                cape_file = os.path.join(self.capes_folder, f"{self.uuid}_cape.png")
                with open(cape_file, "wb") as file:
                    file.write(cape_response.content)
                #print(f"Cape image successfully saved as {cape_file}")
            else:
                print(f"Error fetching cape: {cape_response.status_code} - {cape_response.reason}")

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching capes: {e}")


    def write_playerdata(self):
        output_file = "./output_data/usernames.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        data = {
            "usermap": username_map,
            "uuids": list(username_map.keys()),
            "usernames": list(username_map.values())
        }
        with open(output_file, "w") as file_handler:
            json.dump(data, file_handler, indent=4)
        #print(f"Usernames data successfully saved to {output_file}")
    

    def generate_achievement_report(self):
        """
        Generate a JSON file for the current UUID that lists all advancements with completed and incomplete criteria,
        using the external advancement_criteria.json for multi-part advancements.
        Filters out advancements with the recipe tag and separates non-Minecraft advancements.
        """
        advancements_path = f"../world/advancements/{self.uuid}.json"
        missing_criteria_path = "./static/advancement_criteria.json"
        output_path = f"./output_data/advancements_reports/advancements_report_{self.uuid}.json"

        if not os.path.exists(advancements_path):
            print(f"Advancements file for UUID {self.uuid} does not exist.")
            return

        if not os.path.exists(missing_criteria_path):
            print(f"Advancement criteria file '{missing_criteria_path}' does not exist.")
            return

        try:
            with open(advancements_path, "r") as file:
                advancements_data = json.load(file)

            with open(missing_criteria_path, "r") as file:
                missing_criteria_data = json.load(file)

            multi_part_advancements = missing_criteria_data.get("multi_part_advancements", {})
            other_advancements = missing_criteria_data.get("other_advancements", {})
            
            report = {"multi_part_advancements": {}, "other_advancements": {}}
            for advancement, details in advancements_data.items():
                if not isinstance(details, dict):
                    #print(f"Skipping invalid data for advancement {advancement}: {details}")
                    continue  # Skip non-dictionary entries

                # Skip advancements with the "recipe" tag
                if "recipe" in advancement:
                    # print(f"Skipping recipe advancement: {advancement}")
                    continue
                
                if "minecraft" not in advancement:
                    continue
                
                if "root" in advancement:
                    continue

                # Skip advancements with the "root" tag
                if "root" in advancement:
                    # print(f"Skipping root advancement: {advancement}")
                    continue

                if advancement in multi_part_advancements:
                    # print(list(details["criteria"].keys()))
                    if len(list(details["criteria"].keys())) == multi_part_advancements[advancement]["requirements_num"]:
                        # print("yes")
                        multi_part_advancements[advancement]["done"] = True
                        
                    else:
                        multi_part_advancements[advancement]["done"] = False
                        multi_part_advancements[advancement]["current_progress"] = list(details["criteria"].keys())
                        multi_part_advancements[advancement]["progress"] = f"{len(list(details['criteria'].keys())) / multi_part_advancements[advancement]['requirements_num'] * 100}%"
                        # print(f"no, {len(list(details["criteria"].keys()))} / {multi_part_advancements[advancement]["requirements_num"]}")
                    report["multi_part_advancements"][advancement] = multi_part_advancements[advancement]
                else:
                    other_advancements[advancement]["done"] = True
                    report["other_advancements"][advancement] = other_advancements[advancement]


            # report = {"multi_part_advancements": multi_part_advancements, "other_advancements": other_advancements}
            # Write the report to an output JSON file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as json_file:
                json.dump(report, json_file, indent=4)

            # print(f"Advancement report successfully saved to {output_path}")
        except Exception as e:
            print(f"An error occurred while processing advancements for UUID {self.uuid}: {e}")


    def convert_stats_to_simplified_json(self):
        """
        Convert the ../world/stats/<uuid>.json files into simplified JSONs
        and strip out block and item stats.
        """
        stats_path = f"../world/stats/{self.uuid}.json"
        output_path = f"./output_data/simplified_stats/simplified_stats_{self.uuid}.json"

        if not os.path.exists(stats_path):
            print(f"Stats file for UUID {self.uuid} does not exist.")
            return

        try:
            with open(stats_path, "r") as file:
                stats_data = json.load(file)

            # Filter out everything except the 'minecraft:custom' category under 'stats'
            simplified_stats = {
                "stats": {
                    "minecraft:custom": stats_data.get("stats", {}).get("minecraft:custom", {})
                }
            }

            # Write the simplified stats to a JSON file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as json_file:
                json.dump(simplified_stats, json_file, indent=4)
                

            #print(f"Simplified stats successfully saved to {output_path}")
        except Exception as e:
            print(f"An error occurred while processing stats for UUID {self.uuid}: {e}")





# Example usage
if __name__ == "__main__":
    try:
        dummy = MinecraftStatsHandler("dummy_uuid")
        for player_uuid in dummy.folder:
            try:
                player = MinecraftStatsHandler(player_uuid)
                result = player.get_minecraft_usernames()
                if isinstance(result, dict) and "name" in result:
                    #print(f"Username: {result['name']}")
                    player.get_minecraft_skins()

                    # Generate advancement report
                    player.generate_achievement_report()

                    # Convert stats to simplified JSON
                    player.convert_stats_to_simplified_json()

                    # Grab cape from capes.dev
                    player.get_minecraft_capes()
                    #print("")
                else:
                    print(result)
            except Exception as e:
                print(f"An error occurred with UUID {player_uuid}: {e}")
        dummy.write_playerdata()
    except Exception as main_e:
        print(f"An error occurred in the main execution: {main_e}")
