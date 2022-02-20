import sys
import pathlib
import zipfile
import json
import urllib.request
import urllib.error
import html.parser
import re
import base64

doc_url = 'https://minecraft.fandom.com/wiki/Module:InvSprite'
wiki_url_base = 'https://minecraft.fandom.com/wiki'
block_icon_size = 48


icon_force_asset = {
    'minecraft:acacia_door', 'minecraft:activator_rail', 'minecraft:bamboo', 'minecraft:birch_door',
    'minecraft:black_candle', 'minecraft:blue_candle', 'minecraft:blue_orchid', 'minecraft:brown_candle',
    'minecraft:brown_mushroom', 'minecraft:campfire', 'minecraft:candle', 'minecraft:clock', 'minecraft:cornflower',
    'minecraft:crimson_door', 'minecraft:cyan_candle', 'minecraft:dandelion', 'minecraft:dark_oak_door',
    'minecraft:detector_rail', 'minecraft:gray_candle', 'minecraft:green_candle', 'minecraft:iron_bars',
    'minecraft:iron_door', 'minecraft:ladder', 'minecraft:lever', 'minecraft:light_blue_candle',
    'minecraft:light_gray_candle', 'minecraft:lilac', 'minecraft:lily_of_the_valley', 'minecraft:lime_candle',
    'minecraft:magenta_candle', 'minecraft:oak_door', 'minecraft:orange_candle', 'minecraft:orange_tulip',
    'minecraft:oxeye_daisy', 'minecraft:peony', 'minecraft:pink_candle', 'minecraft:pink_tulip',
    'minecraft:pointed_dripstone', 'minecraft:poppy', 'minecraft:powered_rail', 'minecraft:purple_candle',
    'minecraft:rail', 'minecraft:red_mushroom', 'minecraft:red_tulip', 'minecraft:redstone_torch',
    'minecraft:rose_bush', 'minecraft:soul_campfire', 'minecraft:soul_torch', 'minecraft:spruce_door',
    'minecraft:sugar_cane', 'minecraft:sunflower', 'minecraft:torch', 'minecraft:tripwire_hook', 'minecraft:vine',
    'minecraft:warped_fungus', 'minecraft:white_candle', 'minecraft:white_tulip', 'minecraft:wither_rose',
    'minecraft:yellow_candle', 'minecraft:cake', 'minecraft:azure_bluet', 'minecraft:jungle_door',
    'minecraft:red_candle', 'minecraft:warped_door'
}

icon_force_wiki = {
    'minecraft:enchanted_golden_apple'
}

icon_asset_overrides = {
    'minecraft:compass': 'compass_16',
    'minecraft:sunflower': 'sunflower_front',
    'minecraft:lilac': 'lilac_front',
    'minecraft:peony': 'peony_top',
    'minecraft:rose_bush': 'rose_bush_top',
    'minecraft:crossbow': 'crossbow_pulling_0'
}

icon_wiki_overrides = {
    'Block of Copper': 'Copper Block',
    'Exposed Copper': 'Exposed Copper Block',
    'Oxidized Copper': 'Oxidized Copper Block',
    'Waxed Block of Copper': 'Copper Block',
    'Waxed Cut Copper': 'Cut Copper',
    'Waxed Exposed Copper': 'Exposed Copper Block',
    'Waxed Exposed Cut Copper': 'Exposed Cut Copper',
    'Waxed Oxidized Copper': 'Oxidized Copper Block',
    'Waxed Oxidized Cut Copper': 'Oxidized Cut Copper',
    'Waxed Weathered Copper': 'Weathered Copper Block',
    'Waxed Weathered Cut Copper': 'Weathered Cut Copper',
    'Weathered Copper': 'Weathered Copper Block',
    'Waxed Cut Copper Slab': 'Cut Copper Slab',
    'Waxed Cut Copper Stairs': 'Cut Copper Stairs',
    'Waxed Exposed Cut Copper Slab': 'Cut Copper Slab',
    'Waxed Exposed Cut Copper Stairs': 'Cut Copper Stairs',
    'Waxed Oxidized Cut Copper Slab': 'Cut Copper Slab',
    'Waxed Oxidized Cut Copper Stairs': 'Cut Copper Stairs',
    'Waxed Weathered Cut Copper Slab': 'Cut Copper Slab',
    'Waxed Weathered Cut Copper Stairs': 'Cut Copper Stairs',
}


def is_texture_asset(s):
    if s.startswith('assets/minecraft/textures/item/'):
        return True
    if s.startswith('assets/minecraft/textures/block/'):
        return True
    if s == 'assets/minecraft/textures/gui/container/crafting_table.png':
        return True
    return False


def is_recipe_json(s):
    return s.startswith('data/minecraft/recipes/') and s.endswith('.json')


def is_tag_json(s):
    return s.startswith('data/minecraft/tags/items/') and s.endswith('.json')


def is_lang_json(s):
    return s == 'assets/minecraft/lang/en_us.json'


class WikiParser(html.parser.HTMLParser):
    def __init__(self, block_name):
        super().__init__()
        self.block_name = block_name
        self.in_imagearea = False
        self.div_level = -1
        self.image_ext = None
        self.image_url = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'div' and 'infobox-imagearea' in dict(attrs).get('class', ''):
            self.in_imagearea = True
            self.div_level = 0
        elif self.in_imagearea and tag == 'img':
            attr_dict = dict(attrs)
            file_name_pattern = rf'{re.escape(self.block_name)}( \(floor\))?( \((UD|N|S|\d+)\))?( [JB]E\d+(-[a-z]\d)?)*.(?P<ext>png|gif)'
            if self.image_url is None:
                m = re.match(file_name_pattern, attr_dict.get('alt'))
                if m:
                    self.image_ext = m.group('ext')
                    self.image_url = attr_dict.get('data-src') or attr_dict.get('src')
                    print(f'found {self.block_name}')
        elif self.in_imagearea and tag == 'div':
            self.div_level += 1

    def handle_endtag(self, tag):
        if tag == 'div':
            self.div_level -= 1
            if self.div_level < 0:
                self.in_imagearea = False


def expand_ingredient_choices(ingredient_choices, ingredient_tags):
    item_choices = set()
    tag_choices = set()
    if type(ingredient_choices) != list:
        ingredient_choices = [ingredient_choices]
    for ingredient_choice in ingredient_choices:
        if 'item' in ingredient_choice:
            item_choices.add(ingredient_choice['item'])
        else:
            tag_choices.add(ingredient_choice['tag'])
    while tag_choices:
        new_tag_choices = set()
        for tag_choice in tag_choices:
            for tag_element in ingredient_tags.get(tag_choice.replace('minecraft:', ''))['values']:
                if tag_element.startswith('#'):
                    new_tag_choices.add(tag_element[1:])
                else:
                    item_choices.add(tag_element)
        tag_choices = new_tag_choices
    return item_choices


def extract_item_ids(crafting_recipes, ingredient_tags):
    item_ids = set()
    for recipe in crafting_recipes:
        item_ids.add(recipe['result']['item'])
        if recipe['type'] == 'minecraft:crafting_shapeless':
            for ingredient_choices in recipe['ingredients']:
                for ingredient_choice in expand_ingredient_choices(ingredient_choices, ingredient_tags):
                    item_ids.add(ingredient_choice)
        elif recipe['type'] == 'minecraft:crafting_shaped':
            for _, ingredient_choices in recipe['key'].items():
                for ingredient_choice in expand_ingredient_choices(ingredient_choices, ingredient_tags):
                    item_ids.add(ingredient_choice)
    return item_ids


def get_block_icon(block_id, name):
    if block_id in icon_force_asset:
        return get_item_icon(block_id, name)
    name = icon_wiki_overrides.get(name, name)
    wiki_parser = WikiParser(name)
    wiki_url = f'{wiki_url_base}/{name.replace(" ", "_")}'
    print(f'loading {wiki_url}')
    try:
        with urllib.request.urlopen(wiki_url) as req:
            wiki_parser.feed(req.read().decode('utf-8'))
    except urllib.error.HTTPError:
        raise RuntimeError(f'failed to fetch wiki page {wiki_url}')
    if not wiki_parser.image_url:
        print(f'failed to extract image icon for {name}')
        return ''
    image_url = wiki_parser.image_url.rsplit('/', 1)[0] + f'/{block_icon_size}'
    res = None
    while res is None:
        try:
            with urllib.request.urlopen(image_url) as req:
                res = req.read()
        except urllib.error.HTTPError:
            print(f'failed to fetch image {image_url}, retrying...')
            time.sleep(1)
    image_types_by_ext = {'png': 'png', 'gif': 'webp'}
    image_type = image_types_by_ext.get(wiki_parser.image_ext, 'png')
    return f'data:image/{image_type};base64,' + base64.b64encode(res).decode('utf-8')


def get_item_icon(item_id, name):
    if item_id in icon_force_wiki:
        return get_block_icon(item_id, name)
    filename = icon_asset_overrides.get(item_id, item_id.replace('minecraft:', ''))
    if pathlib.Path(f'tmp/minecraft/{filename}.png').is_file():
        with open(f'tmp/minecraft/{filename}.png', 'rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
    return ''


if __name__ == '__main__':
    if len(sys.argv) > 1:
        jar_path = sys.argv[1]
    else:
        jar_path = pathlib.Path.home() / '.local/share/multimc/libraries/com/mojang/minecraft/1.18.1/minecraft-1.18.1-client.jar'
    recipes = []
    tags = {}
    pathlib.Path('tmp/minecraft').mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar_path, 'r') as jar:
        for zip_info in jar.infolist():
            if zip_info.is_dir():
                continue
            if is_texture_asset(zip_info.filename):
                zip_info.filename = pathlib.Path(zip_info.filename).name
                jar.extract(zip_info, 'tmp/minecraft')
            elif is_recipe_json(zip_info.filename):
                recipe_dict = json.loads(jar.read(zip_info.filename))
                if recipe_dict['type'] in ('minecraft:crafting_shaped', 'minecraft:crafting_shapeless'):
                    recipes.append(recipe_dict)
            elif is_tag_json(zip_info.filename):
                tags[pathlib.Path(zip_info.filename).stem] = json.loads(jar.read(zip_info.filename))
            elif is_lang_json(zip_info.filename):
                lang = json.loads(jar.read(zip_info.filename))
    with open('static/recipes.json', 'w') as f:
        json.dump(recipes, f)
    with open('static/tags.json', 'w') as f:
        json.dump(tags, f)

    items = {}
    relevant_item_ids = extract_item_ids(recipes, tags)
    for relevant_item_id in relevant_item_ids:
        if item_name := lang.get(f'item.minecraft.{relevant_item_id.split(":")[1]}'):
            item_icon = get_item_icon(relevant_item_id, item_name)
            items[relevant_item_id] = {'name': item_name, 'icon': item_icon}
        elif block_name := lang.get(f'block.minecraft.{relevant_item_id.split(":")[1]}'):
            block_icon = get_block_icon(relevant_item_id, block_name)
            items[relevant_item_id] = {'name': block_name, 'icon': block_icon}
        else:
            raise RuntimeError(f'cannot find name for {relevant_item_id}')
    with open('static/items.json', 'w') as f:
        json.dump(items, f, indent=2)
