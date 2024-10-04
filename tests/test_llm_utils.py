import datetime
import json

from tale.image_gen.automatic1111 import Automatic1111
from tale.llm.contexts.CharacterContext import CharacterContext
from tale.llm.contexts.FollowContext import FollowContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext
import tale.llm.llm_cache as llm_cache
from tale import mud_context
from tale import zone
from tale import util
from tale.base import Location
from tale.coord import Coord
from tale.json_story import JsonStory
from tale.llm.llm_utils import LlmUtil
from tale.llm.responses.ActionResponse import ActionResponse
from tale.llm.responses.FollowResponse import FollowResponse
from tale.player import Player, PlayerConnection
from tale.races import UnarmedAttack
from tale.story import MoneyType
from tale.tio.console_io import ConsoleIo
from tale.zone import Zone
from tests.supportstuff import FakeIoUtil
import tale.parse_utils as parse_utils
from tale.driver_if import IFDriver

class TestLlmUtils():

    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    
    llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil

    story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story_config_empty.json')))
    
    story.init(driver)

    def test_read_items(self):
        character_card = "[Norhardt; gender: m; age: 56; occupation: ; personality: An experienced explorer ; appearance: A grizzled old man, with parch; items:map]"
        items_array = character_card.split('items:')[1].split(']')[0]
        #items = json.loads(items_array)
        assert('map' in items_array)
        
    def test_evoke(self):
        evoke_string = 'test response'
        self.llm_util.io_util = FakeIoUtil(response=evoke_string)
        
        self.llm_util.set_story(self.story)
        result = self.llm_util.evoke(message='test evoke')
        assert(result)
        assert(llm_cache.get_looks([llm_cache.generate_hash('test evoke')]) == evoke_string)

    def test_evoke_extra_context(self):
        evoke_string = 'test response'
        self.llm_util.io_util = FakeIoUtil(response=evoke_string)
        
        self.llm_util.set_story(self.story)
        result = self.llm_util.evoke(message='test evoke', extra_context='test extra context')
        assert(result)
        assert(llm_cache.get_looks([llm_cache.generate_hash('test evoke')]) == evoke_string)

    def test_generate_character(self):
        character_string = json.dumps(parse_utils.load_json('tests/files/test_character.json'))
        self.llm_util._character.io_util = FakeIoUtil(response = character_string)
        context = CharacterContext(key_words='test key words', story_type='test story type', story_context='test story context', world_info='test world info', world_mood=0)
        result = self.llm_util._character.generate_character(character_context=context)
        assert(result)


    def test_perform_idle_action(self):
        # mostly testing that prompt works
        self.llm_util.set_story(self.story)
        self.llm_util._character.io_util.response = 'Walk to the left'
        location = Location(name='Test Location')
        actions = self.llm_util.perform_idle_action(character_name='Norhardt', location = location, character_card= '{}', sentiments= {}, last_action= '')
        assert(actions == 'Walk to the left')

    def test_perform_travel_action(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = 'West'
        result = self.llm_util._character.perform_travel_action(character_name='Norhardt', location = Location(name='Test Location'), character_card= '{}', locations= [], directions= [])
        assert(result == 'West')

    def test_generate_dialogue(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = ['{"response":"Hello there", "sentiment":"cheerful", "give":"ale"}']
        result, item, sentiment = self.llm_util.generate_dialogue(conversation='test conversation', 
                                                            character_card='{}', 
                                                            character_name='Norhardt', 
                                                            target='Arto', 
                                                            target_description='{}', 
                                                            sentiment='cheerful', 
                                                            location_description='{}')
        assert(result == 'Hello there')
        assert(item == 'ale')
        assert(sentiment == 'cheerful')

        
    def test_generate_dialogue_json(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = ["{\n  \"response\": \"Autumn greets Test character with a warm smile, her golden hair shining in the sunlight. She returns the greeting, her voice filled with kindness, \'Hello there, how can I assist you today?\'\"\n}"]
        result, item, sentiment = self.llm_util.generate_dialogue(conversation='test conversation', 
                                                            character_card='{}', 
                                                            character_name='Norhardt', 
                                                            target='Arto', 
                                                            target_description='{}', 
                                                            sentiment='cheerful', 
                                                            location_description='{}')
        assert(result.startswith("Autumn greets Test character")) 
        assert(item == None)
        assert(sentiment == None)

    def test_free_form_action(self):
        self.llm_util._character.io_util.response = '{"action":"test_action", "text":"test response", "target":"test target", "item":"test item"}'
        location = Location(name='Test Location')
        self.llm_util.set_story(self.story)
        result = self.llm_util.free_form_action(location=location, character_name='', character_card='', event_history='')[0] # type: list
        assert(result)
        assert(result.action == 'test_action')
        assert(result.text == 'test response')
        assert(result.target == 'test target')
        assert(result.item == 'test item')

    def test_free_form_action_lists(self):
        self.llm_util._character.io_util.response = '{"action":["test_action"], "text":["test response"], "target":["test target"], "item":["test item"]}'
        location = Location(name='Test Location')
        self.llm_util.set_story(self.story)
        result = self.llm_util.free_form_action(location=location, character_name='', character_card='', event_history='')[0] # type: ActionResponse
        assert(result)
        assert(result.action == 'test_action')
        assert(result.text == 'test response')
        assert(result.target == 'test target')
        assert(result.item == 'test item')

    def test_free_form_action_dict(self):
        self.llm_util._character.io_util.response = '{"action":{"action":"test_action"}, "target":{"name":"test target"}}'
        location = Location(name='Test Location')
        self.llm_util.set_story(self.story)
        result = self.llm_util.free_form_action(location=location, character_name='', character_card='', event_history='')[0] # type: ActionResponse
        assert(result.action == 'test_action')
        assert(result.target == 'test target')

    def test_free_form_action_multi(self):
        self.llm_util._character.io_util.response = '[{"action":"test_action", "text":"test response", "target":"test target", "item":"test item"},{"action":"test_action2"},{"action":"test_action3"}]'
        location = Location(name='Test Location')
        self.llm_util.set_story(self.story)
        result = self.llm_util.free_form_action(location=location, character_name='', character_card='', event_history='') # type: list
        assert(len(result) == 3)
        assert(result[0].action == 'test_action')
        assert(result[0].text == 'test response')
        assert(result[0].target == 'test target')
        assert(result[0].item == 'test item')
        assert(result[1].action == 'test_action2')
        assert(result[2].action == 'test_action3')

    def test_init_image_gen(self):
        self.llm_util._init_image_gen("Automatic1111")
        assert self.llm_util._image_gen.__class__ == Automatic1111().__class__

    def test_request_follow_true(self):
        self.llm_util._character.io_util.response = '{"response":"yes", "reason":"test reason"}'
        location = Location(name='Test Location')
        follow_context = FollowContext(story_context='test context', story_type='test type', character_name='Norhardt', character_card='{}', event_history='{}', location=location, asker_name='Arto', asker_card='{}', asker_reason='{}')
        result = self.llm_util._character.request_follow(follow_context) # type: FollowResponse
        assert(result.follow == True)
        assert(result.reason == 'test reason')

    def test_describe_day_cycle_transition(self):
        player = Player("test_player", "m")
        location = Location(name='Test Location')
        location.init_inventory([player])
        pc = PlayerConnection(player, ConsoleIo(None))
        self.llm_util.io_util.response = 'shadows lengthen as the sun dips below the horizon, casting a golden glow over the landscape. The air grows cooler, and the sounds of nocturnal creatures begin to fill the night.'
        self.llm_util.set_story(self.story)
        result = self.llm_util.describe_day_cycle_transition(pc, 'day', 'dusk')
        assert(result.startswith('shadows lengthen'))
        assert('shadows lengthen' in pc.get_output())


class TestWorldBuilding():

    generated_location = '{"name": "Outside", "description": "A barren wasteland of snow and ice stretches as far as the eye can see. The wind howls through the mountains like a chorus of banshees, threatening to sweep away any unfortunate soul caught outside without shelter.", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": [{"name":"wolf", "body":"Creature", "unarmed_attack":"BITE", "hp":10, "level":10}]}'
    
    generated_location_extra = '{"Outside": { "description": "A barren wasteland of snow and ice stretches", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": []}}'
    
    generated_zone = '{"name":"Test Zone", "description":"A test zone", "level":10, "mood":-2, "races":["human", "elf", "dwarf"], "items":["sword", "shield"]}'
    
    def setup_method(self):
         
        self.story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story_config_empty.json')))
        self.story.config.world_mood = 0
        self.story.config.world_info = "A test world"
        self.driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        self.driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        self.driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.MODERN)
        self.llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil
        self.story.init(self.driver)

    def test_generate_start_location(self):
        self.llm_util._world_building.io_util.response='{"name": "Greenhaven", "exits": [{"direction": "north", "name": "Misty Meadows", "description": "A lush and misty area filled with rolling hills and sparkling streams. The air is crisp and refreshing, and the gentle chirping of birds can be heard throughout."}, {"direction": "south", "name": "Riverdale", "description": "A bustling town nestled near a winding river. The smell of freshly baked bread and roasting meats fills the air, and the sound of laughter and chatter can be heard from the local tavern."}, {"direction": "east", "name": "Forest of Shadows", "description": "A dark and eerie forest filled with twisted trees and mysterious creatures. The air is thick with an ominous energy, and the rustling of leaves can be heard in the distance."}], "items": [], "npcs": []}'
        location = Location(name='', descr='on a small road outside a village')
        result = self.llm_util._world_building.generate_start_location(location, 
                                                       context=WorldGenerationContext(story_type='',
                                                       story_context='',
                                                       world_info='',
                                                       world_mood=0),
                                                       zone_info={})
        new_locations = result.new_locations
        exits = result.exits
        location = Location(name=location.name, descr=location.description)
        assert(location.name == 'Greenhaven')
        assert(location.title == 'Greenhaven')
        assert(location.description == 'on a small road outside a village')
        assert(exits[0].name == 'misty meadows')
        assert(exits[1].name == 'riverdale')
        assert(new_locations[0].name == 'Misty Meadows')
        assert(new_locations[1].name == 'Riverdale')

    def test_generate_start_location_2(self):
        self.llm_util._world_building.io_util.response='{"name": "Oakwood Glade", "exits": [{"direction": "north", "name": "Moonlit Mire", "description": "A dark and eerie bog, home to strange creatures and hidden treasures."}, {"direction": "south", "name": "Raven\'s Peak", "description": "A rugged mountain peak, shrouded in mystery."}, {"direction": "west", "name": "Willow\'s Edge", "description": "A secluded grove, filled with ancient magic."}], "items": [{"name": "Rare Flower", "type": "Other", "short_descr": "A delicate, glowing flower, said to have healing properties."}, {"name": "Mystic Staff", "type": "Wearable", "short_descr": "A staff imbued with ancient magic, granting the wielder incredible power."}, {"name": "Glimmering Gem", "type": "Item", "short_descr": "A rare and valuable gemstone, sought after by collectors."}], "npcs": [{"name": "Eira", "sentiment": "friendly", "race": "female", "level": 5, "description": "A wise and gentle druid, known for her healing magic."}]}'
        location = Location(name='', descr='on a small road outside a village')
        result = self.llm_util._world_building.generate_start_location(location, 
                                                       context=WorldGenerationContext(story_type='',
                                                       story_context='',
                                                       world_info='',
                                                       world_mood=0),
                                                       zone_info={},)
        
        location = Location(name=location.name, descr=location.description)
        assert(location.name == 'Oakwood Glade')
        assert(location.title == 'Oakwood Glade')
        assert(location.description == 'on a small road outside a village')

    def test_generate_start_zone(self):
        # mostly for coverage
        self.llm_util._world_building.io_util.response = self.generated_zone

        result = self.llm_util.generate_start_zone(location_desc='',
                                                   story_type='',
                                                   story_context='',
                                                   world_info={"info":"", "world_mood":0})
        assert(result.name == 'Test Zone')
        assert(result.races == ['human', 'elf', 'dwarf'])

    def test_generate_world_items(self):
        self.llm_util._world_building.io_util.response = '{"items":[{"name": "sword", "type": "Weapon","value": 100}, {"name": "shield", "type": "Armor", "value": 60}]}'
        result = self.llm_util._world_building.generate_world_items(world_generation_context=WorldGenerationContext(story_context='',story_type='',world_info='',world_mood=0))
        assert(result.valid)
        assert(len(result.items) == 2)
        sword = result.items[0]
        assert(sword['name'] == 'sword')
        shield = result.items[1]
        assert(shield['name'] == 'shield')

        self.llm_util._world_building.io_util.response = ''
        result = self.llm_util._world_building.generate_world_items(world_generation_context=WorldGenerationContext(story_context='',story_type='',world_info='',world_mood=0))
        assert not result.valid
        assert(len(result.items) == 0)


    def test_generate_world_creatures(self):
        # mostly for coverage
        self.llm_util._world_building.io_util.response = '{"creatures":[{"name": "dragon", "body": "Creature", "unarmed_attack": "BITE", "hp":100, "level":10}]}'
        result = self.llm_util._world_building.generate_world_creatures(world_generation_context=WorldGenerationContext(story_context='',story_type='',world_info='',world_mood=0))
        assert(result.valid)
        assert(len(result.creatures) == 1)
        dragon = result.creatures[0]
        assert(dragon["name"] == 'dragon')
        assert(dragon["hp"] == 100)
        assert(dragon["level"] == 10)
        assert(dragon["unarmed_attack"] == UnarmedAttack.BITE.name)

        self.llm_util._world_building.io_util.response = ''
        result = self.llm_util._world_building.generate_world_creatures(world_generation_context=WorldGenerationContext(story_context='',story_type='',world_info='',world_mood=0))
        assert not result.valid
        assert(len(result.creatures) == 0)

    def test_get_neighbor_or_generate_zone(self):
        """ Tests the get_neighbor_or_generate_zone method of llm_utils.
        """
        self.llm_util._world_building.io_util.response = self.generated_zone
        zone = Zone('Current zone', description='This is the current zone')
        zone.neighbors['east'] = Zone('East zone', description='This is the east zone')
        
        # near location, returning current zone
        current_location = Location(name='Test Location')
        current_location.world_location = Coord(0, 0, 0)
        target_location = Location(name='Target Location')
        target_location.world_location = Coord(1, 0, 0)
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')
        
        # far location, neighbor exists, returning east zone
        current_location.world_location = Coord(10, 0, 0)
        target_location.world_location = Coord(11, 0, 0)
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the east zone')
        
        # far location, neighbor does not exist, generating new zone
        self.llm_util.io_util.response = self.generated_zone
        self.llm_util.set_story(self.story)
        current_location.world_location = Coord(-10, 0, 0)
        target_location.world_location = Coord(-11, 0, 0)
        new_zone = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location)
        assert(self.story.get_zone(new_zone.name))
        assert(new_zone.get_info()['description'] == 'A test zone')

        # test add a zone with same name
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')
        
        # test with non valid json
        self.llm_util.io_util.response = '{"name":test}'
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')

        # test with valid json but not valid zone
        self.llm_util.io_util.response = '{}'
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')


    def test_build_location(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util._world_building.io_util.response = self.generated_location
        self.llm_util.set_story(self.story)
        
        response, spawner = self.llm_util.build_location(location, exit_location_name, zone_info={})
        assert(len(response.new_locations) == 2)
        assert spawner
        assert spawner.mob_type.name == 'wolf'

    def test_build_location_extra_json(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util._world_building.io_util.response = self.generated_location_extra
        self.llm_util.set_story(self.story)
        result, _ = self.llm_util.build_location(location, exit_location_name, zone_info={})

        assert(len(result.new_locations) == 2)

    def test_build_location_no_description(self):
        location = Location(name='The Red Rock Saloon')
        exit_location_name = 'Cactus Cove'
        self.llm_util._world_building.io_util.response = '{"exits": [{"direction": "north", "name": "The Dusty Trail", "description": "A winding path through the cacti, leading deeper into the frontier."}, {"direction": "south", "name": "The Oasis of Eternal Springs", "description": "A lush and verdant oasis, rumored to hold ancient secrets."}, {"direction": "east", "name": "The Cactus Canyon", "description": "A treacherous gorge, home to the fierce Cactus Worm."}], "items": [{"name": "Cactus Flower", "description": "A rare and beautiful bloom, said to have healing properties."}, {"name": "Cactus Juice", "description": "A refreshing drink, made from the rare cactus fruit."}, {"name": "Cactus Shield", "description": "A sturdy shield, crafted from the toughest cactus spines."}], "npcs": []}'
        self.llm_util.set_story(self.story)
        result, _ = self.llm_util.build_location(location, exit_location_name, zone_info={})

        assert(location.description == 'Cactus Cove')
        assert(len(result.new_locations) == 3)

    def test_validate_zone(self):
        center = Coord(5, 0, 0)
        zone = self.llm_util._world_building.validate_zone(json.loads(self.generated_zone), center=center)
        assert(zone)
        assert(zone.name == 'Test Zone')
        assert(zone.description == 'A test zone')
        assert(zone.races == ['human', 'elf', 'dwarf'])
        assert(zone.items == ['sword', 'shield'])
        assert(zone.center == center)
        assert(zone.level == 10)
        assert(zone.mood == -2)
        
    def test_issue_1_build_location(self):
        z = zone.from_json(json.loads('{   "name": "Whispering Meadows",   "description": "Whispering Meadows is a serene and idyllic area nestled within Eldervale. It is a sprawling expanse of lush green meadows, dotted with colorful wildflowers swaying gently in the breeze. The sweet fragrance of blooming lavender fills the air, creating an enchanting atmosphere. The meadows are home to a variety of friendly creatures, and the soothing whispers of the wind carry tales of peace and harmony. With its tranquil beauty, Whispering Meadows provides the perfect backdrop for a cosy social and farming experience.",   "races": ["Fairie", "Centaur", "Unicorn", "Pixie", "Sylph"],   "items": ["Enchanted Seeds (plantable)", "Harvesting Scythe", "Rainbow Fruit Basket", "Magic Beehive", "Fairy Lantern"],   "mood": "friendly",   "level": 1 }'))
        
        location = Location(name='Whispering Meadows')
        exit_location_name = 'Harvest Grove'
        self.llm_util._world_building.io_util.response = '{"description": "Whispering Meadows is a serene and idyllic area nestled within Eldervale. It is a sprawling expanse of lush green meadows, dotted with colorful wildflowers swaying gently in the breeze. The sweet fragrance of blooming lavender fills the air, creating an enchanting atmosphere. The meadows are home to a variety of friendly creatures, and the soothing whispers of the wind carry tales of peace and harmony. With its tranquil beauty, Whispering Meadows provides the perfect backdrop for a cosy social and farming experience.",   "exits": [     {       "direction": "North",       "name": "Harvest Grove",       "short_descr": "A hidden pathway leads to the Harvest Grove, where trees bear fruits of extraordinary flavors."     },     {       "direction": "East",       "name": "Glimmering Glade",       "short_descr": "A shimmering path leads to the Glimmering Glade, where fireflies illuminate secrets of the woods."     },     {       "direction": "West",       "name": "Twilight Meadow",       "short_descr": "A mysterious trail leads to the Twilight Meadow, where moonlight reveals hidden wonders to explorers."     }   ],   "items": [     "Enchanted Seeds (plantable)",     "Harvesting Scythe",     "Rainbow Fruit Basket",     "Magic Beehive",     "Fairy Lantern",     "Mystical Herb Pouch",     "Whispering Wind Chime",     "Dreamcatcher Necklace"   ],   "npcs": [     {       "name": "Amelia",       "sentiment": "friendly",       "race": "Pixie",       "gender": "f",       "level": 3,       "description": "A mischievous Pixie with wings shimmering in various hues. She loves to play pranks but has a heart of gold."     },     {       "name": "Basil",       "sentiment": "friendly",       "race": "Centaur",       "gender": "m",       "level": 5,       "description": "A gentle Centaur with a serene disposition. He imparts wisdom with every gallop and nurtures plants with care."     },     {       "name": "Celeste",       "sentiment": "friendly",       "race": "Fairie",       "gender": "n",       "level": 4,       "description": "A gracious Fairie with shimmering wings that radiate ethereal light. She ensures the beauty of Whispering Meadows remains eternal."     }   ] }'
        self.llm_util.set_story(self.story)
        response, spawner = self.llm_util.build_location(location, exit_location_name, zone_info=z.get_info())
        assert(len(response.new_locations) == 2)

    def test_chatgpt_generated_story(self):
        item_response = '{   "items": [     {       "name": "Enchanted Rose",       "type": "Other",       "short_descr": "A magical rose that never withers",       "level": 1,       "value": 50     },     {       "name": "Tea Set",       "type": "Wearable",       "short_descr": "A delightful tea set for elegant gatherings",       "level": 2,       "value": 80     },     {       "name": "Winged Boots",       "type": "Wearable",       "short_descr": "Boots that allow the wearer to fly short distances",       "level": 3,       "value": 120     },     {       "name": "Pixie\'s Elixir",       "type": "Health",       "short_descr": "A revitalizing potion that restores health",       "level": 4,       "value": 150     },     {       "name": "Jester\'s Hat",       "type": "Wearable",       "short_descr": "A colorful hat that brings joy and laughter",       "level": 5,       "value": 200     },     {       "name": "Rainbow Wand",       "type": "Weapon",       "short_descr": "A wand that shoots dazzling rainbow projectiles",       "level": 6,       "value": 250     },     {       "name": "Golden Oz Coin",       "type": "Money",       "short_descr": "A rare and valuable coin from the Land of Oz",       "level": 7,       "value": 300     }   ] }'
        creature_response = '{"creatures": [   {"name": "Whisperwing",    "body": "Small dragon",    "mass": 10,    "hp": 50,    "level": 3,    "unarmed_attack": "CLAWS",    "short_descr": "A colorful dragon with feathered wings and a mischievous personality."},    {"name": "Glowbug",    "body": "Bioluminescent insect",    "mass": 1,    "hp": 10,    "level": 1,    "unarmed_attack": "BITE",    "short_descr": "A tiny insect that emits a soft, soothing glow in the dark."},    {"name": "Fluffpuff",    "body": "Fluffy creature",    "mass": 5,    "hp": 25,    "level": 2,    "unarmed_attack": "TAIL",    "short_descr": "A round, fluffy creature with a cuddly appearance and a playful nature."},    {"name": "Coralite",    "body": "Coral-like sea creature",    "mass": 20,    "hp": 75,    "level": 4,    "unarmed_attack": "TENTACLES",    "short_descr": "A graceful creature that dwells in underwater caves, adorned with vibrant coral-like formations."},    {"name": "Whiskerbeast",    "body": "Feline creature",    "mass": 15,    "hp": 60,    "level": 3,    "unarmed_attack": "CLAWS",    "short_descr": "A playful and agile creature with long, fluffy whiskers and a shimmering fur coat."} ]}'
        zone_desc = '{   "name": "Cozy Meadows",   "description": "A tranquil expanse of lush green meadows, dotted with colorful wildflowers and tall, swaying grass. The air is filled with the sweet fragrance of nature, inviting weary wanderers to rest and enjoy the serene surroundings. Sunlight filters through the canopy of trees, casting golden rays upon the meadows and creating a picturesque setting for picnics and leisurely strolls. Squirrels chase each other playfully, and birds sing melodious tunes from the branches above. It\'s a perfect place to unwind and find respite from the troubles of the world.",   "races": ["whisperwing", "glowbug", "fluffpuff", "coralite", "whiskerbeast"],   "items": {     "enchanted rose": "flower",     "tea set": "utensils",     "winged boots": "footwear",     "pixie\'s elixir": "potion",     "jester\'s hat": "headgear"   },   "mood": "friendly",   "level": 1 }'
        location_desc = '{   "description": "A gentle transition between the lush meadows and the enchanting forests, Meadow\'s Edge is a place where tranquility meets adventure. Tall grass sways in the breeze, beckoning explorers to venture further. The air carries the sweet scent of wildflowers, creating a blissful harmony with nature\'s orchestra.",   "exits": [     {"direction": "North", "name": "Whispering Grove", "short_descr": "A mystical grove filled with ancient whispering trees."},     {"direction": "East", "name": "Butterfly Meadow", "short_descr": "A haven for delicate butterflies, fluttering amidst colorful blooms."},     {"direction": "West", "name": "Sunlit Glade", "short_descr": "A sun-dappled glade where rays of light dance upon the moss-covered ground."}   ],   "items": [     {"name": "Songbird Feather", "type": "treasure"},     {"name": "Dewdrop Pendant", "type": "accessory"},     {"name": "Meadowlark Whistle", "type": "instrument"}   ],   "npcs": [     {"name": "Flora", "sentiment": "friendly", "race": "whisperwing", "gender": "f", "level": 2, "description": "A graceful whisperwing with iridescent wings, known for her soothing melodies."},     {"name": "Bramble", "sentiment": "neutral", "race": "fluffpuff", "gender": "m", "level": 3, "description": "A mischievous fluffpuff with a twinkle in his eye, able to shape-shift into various plants."},     {"name": "Corvus", "sentiment": "hostile", "race": "whiskerbeast", "gender": "m", "level": 5, "description": "A fierce whiskerbeast with sleek black fur, his piercing gaze holds a hint of danger."}   ] }'
        location_desc_2 = '{     "description": "A gentle slope leads to Meadow\'s Edge, where wildflowers stretch out as far as the eye can see. Butterflies dance between the blades of grass, creating a kaleidoscope of colors. A babbling brook runs alongside, inviting visitors to dip their toes in its crystal-clear water.",     "exits": [         {"direction": "North", "name": "Whispering Woods", "short_descr": "A mysterious forest filled with ancient trees that whisper secrets to those who dare to listen."},         {"direction": "East", "name": "Glowing Glade", "short_descr": "An enchanted clearing bathed in a soft, ethereal glow, where fireflies dance in mesmerizing patterns."},         {"direction": "South", "name": "Fluffy Fields", "short_descr": "Rolling hills covered in plush tufts of grass, where fluffy sheep graze peacefully under the watchful eye of their shepherd."}     ],     "items": [],     "npcs": [] }'
        location = Location(name='Meadow\'s Edge')
        exit_location_name = 'Sunflower Way'
        self.llm_util.set_story(self.story)
        self.llm_util._world_building.io_util.response = [item_response, creature_response, zone_desc, location_desc, location_desc_2]
        world_items = self.llm_util.generate_world_items(story_context='', 
                                                   story_type='',
                                                   world_mood=0,
                                                   world_info='')
        assert(len(world_items.items) > 0)

        world_creatures = self.llm_util.generate_world_creatures(story_context='', 
                                                   story_type='',
                                                   world_mood=0,
                                                   world_info='')
        assert(len(world_creatures.creatures) > 0)
        
        world_info = {'world_description': '', 'world_mood': 2, 'world_items': world_items, 'world_creatures': world_creatures}
        zone = self.llm_util.generate_start_zone(location_desc='',
                                                   story_type='',
                                                   story_context='',
                                                   world_info=world_info)
        assert(zone)
        response, spawner = self.llm_util.build_location(location, exit_location_name, zone_info=zone.get_info(), world_creatures=world_creatures.creatures, world_items=world_items.items)
        assert(len(response.new_locations) > 0)
        assert(len(response.exits) > 0)
        assert(len(location.items) == 3)
        assert(len(location.livings) == 3)

        location2 = Location(name='Fluffy Fields')
        exit_location_name2 = 'Meadow\'s Edge'


        response, spawner = self.llm_util.build_location(location2, exit_location_name2, zone_info=zone.get_info(), world_creatures=world_creatures, world_items=world_items)
        assert(len(response.new_locations) > 0)
        assert(len(response.exits) > 0)

    def test_generate_random_spawn(self):
        location = Location(name='Outside')
        self.llm_util._world_building.io_util.response = '{"items":["sword"], "npcs":[{"name": "grumpy dwarf", "level":10, "race": "dwarf"}], "mobs":["wolf"]}'

        world_items = [{'name':'sword', 'type': 'Weapon', 'value': 100, 'weapon_type': 'ONE_HANDED'}]
        world_creatures = [{'name': 'wolf', 'body': 'Creature', 'unarmed_attack': 'BITE', 'hp':10, 'level':10}]
        zone_info = zone.from_json(json.loads(self.generated_zone)).get_info()
        world_generation_context = WorldGenerationContext(story_context=self.story.config.context, story_type=self.story.config.type, world_info='', world_mood=0)

        result = self.llm_util._world_building.generate_random_spawn(location, 
                                                            context=world_generation_context,
                                                            zone_info=zone_info,
                                                            world_creatures=world_creatures,
                                                            world_items=world_items)
        assert result
        assert(location.items.pop().name == 'sword')
        assert(location.search_living('grumpy') is not None)
        assert(location.search_living('wolf') is not None)

    def test_generate_random_spawn_empty_world_lists(self):
        mud_context.driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.MODERN)
        # will not generate anything if world lists are empty, for now.
        location = Location(name='Outside')
        self.llm_util._world_building.io_util.response = '{"items":["sword"], "npcs":[{"name": "grumpy dwarf", "level":10, "race": "dwarf"}], "mobs":["wolf"]}'

        world_items = []
        world_creatures = []
        zone_info = zone.from_json(json.loads(self.generated_zone)).get_info()
        world_generation_context = WorldGenerationContext(story_context=self.story.config.context, story_type=self.story.config.type, world_info='', world_mood=0)

        result = self.llm_util._world_building.generate_random_spawn(location, 
                                                            zone_info=zone_info,
                                                            context=world_generation_context,
                                                            world_creatures=world_creatures,
                                                            world_items=world_items)
        assert result
        assert(len(location.items) == 0)
        assert(location.search_living('grumpy') is not None)
        assert(location.search_living('wolf') is None)

    def test_issue_overwriting_exits(self):
        """ User walks west and enters Rocky Cliffs, When returning east, the exits are overwritten."""
        self.llm_util._world_building.io_util.response=['{"name": "Forest Path", "exits": [{"direction": "north", "name": "Mystic Woods", "short_descr": "A dense, misty forest teeming with ancient magic."}, {"direction": "south", "name": "Blooming Meadow", "short_descr": "A lush, vibrant meadow filled with wildflowers and gentle creatures."}, {"direction": "west", "name": "Rocky Cliffs", "short_descr": "A rugged, rocky terrain with breathtaking views of the surrounding landscape."}], "items": [{"name": "enchanted forest amulet", "type": "Wearable", "description": "A shimmering amulet infused with the magic of the forest, granting the wearer a moderate boost to their defense and resistance to harm."}], "npcs": [{"name": "Florabug", "sentiment": "neutral", "race": "florabug", "gender": "m", "level": 5, "description": "A friendly, curious creature who loves to make new friends."}]}',
                                                        '{"description": "A picturesque beach with soft, golden sand and crystal clear waters. The sun shines bright overhead, casting a warm glow over the area. The air is filled with the sound of gentle waves and the cries of seagulls. A few scattered palm trees provide shade and a sense of tranquility.", "exits": [{"direction": "north", "name": "Coastal Caves", "short_descr": "A network of dark, damp caves hidden behind the sandy shores."}, {"direction": "south", "name": "Rocky Cliffs", "short_descr": "A rugged, rocky coastline with steep drop-offs and hidden sea creatures."}, {"direction": "east", "name": "Mermaid\'s Grotto", "short_descr": "A hidden underwater cave system, rumored to be home to magical sea creatures."}], "items": [], "npcs": []}']
        location = Location(name='', descr='on a small road outside a forest')
        result = self.llm_util.generate_start_location(location, 
                                                       story_type='',
                                                       story_context='', 
                                                       zone_info={},
                                                       world_info='',
                                                       world_mood=0)

        location = Location(name=location.name, descr=location.description)
        
        assert((len(result.exits) == 3))
        assert((len(result.new_locations) == 3))
        location.add_exits(result.exits)
        assert((len(location.exits) == 6))
        rocky_cliffs = result.new_locations[2] # type: Location
        assert(rocky_cliffs.name == 'Rocky Cliffs')

        context = WorldGenerationContext(story_context='', story_type='', world_info='', world_mood=0)
        location_response, spawner = self.llm_util._world_building.build_location(rocky_cliffs, 
                                                                            'Rocky Cliffs', 
                                                                            context=context,
                                                                            zone_info={})
        rocky_cliffs.add_exits(location_response.exits)
        assert((len(rocky_cliffs.exits) == 6))
        assert((len(location_response.new_locations) == 2))

    def test_generate_location_empty_response(self):
        self.llm_util._world_building.io_util.response=''
        location = Location(name='Outside')
        result = self.llm_util.generate_start_location(location, 
                                                       story_type='',
                                                       story_context='', 
                                                       zone_info={},
                                                       world_info='',
                                                       world_mood=0)
        assert result.empty()

        self.llm_util._world_building.io_util.response='{}'
        location = Location(name='Outside')
        result = self.llm_util.generate_start_location(location, 
                                                       story_type='',
                                                       story_context='', 
                                                       zone_info={},
                                                       world_info='',
                                                       world_mood=0)
        assert result.empty()

    def test_generate_note_lore(self):
        self.llm_util._quest_building.io_util.response = 'A long lost tale of a hero who saved the world from a great evil.'
        world_generation_context = WorldGenerationContext(story_context=self.story.config.context, story_type=self.story.config.type, world_info='', world_mood=0)

        lore = self.llm_util._world_building.generate_note_lore(context=world_generation_context, zone_info='')
        assert(lore.startswith('A long lost tale'))

    def test_generate_dungeon_locations(self):
        self.llm_util._world_building.io_util.response =' {   "rooms": [   {   "index": 0,   "name": "Entrance to dungeon",   "description": "A dark and ominous entrance to the dungeon, with a sense of foreboding."   },   {   "index": 1,   "name": "Hallway",   "description": "A long and winding hallway, with doors leading off to either side."   },   {   "index": 2,   "name": "Hallway",   "description": "Another long and winding hallway, with doors leading off to either side."   },   {   "index": 3,   "name": "Hallway",   "description": "A narrow and dimly lit hallway, with a sense of claustrophobia."   },   {   "index": 4,   "name": "Hallway",   "description": "A wide and well-lit hallway, with a sense of grandeur."   },   {   "index": 5,   "name": "Hallway",   "description": "A twisting and turning hallway, with a sense of confusion."   },   {   "index": 6,   "name": "Hallway",   "description": "A long and straight hallway, with a sense of monotony."   },   {   "index": 7,   "name": "Hallway",   "description": "A dark and foreboding hallway, with a sense of danger."   },   {   "index": 8,   "name": "Hallway",   "description": "A narrow and winding hallway, with a sense of unease."   },   {   "index": 9,   "name": "Hallway",   "description": "A long and straight hallway, with a sense of tedium."   },   {   "index": 10,   "name": "Hallway",   "description": "A well-lit and grand hallway, with a sense of pride."   },   {   "index": 11,   "name": "Hallway",   "description": "A twisting and turning hallway, with a sense of mystery."   },   {   "index": 12,   "name": "Hallway",   "description": "A dark and foreboding hallway, with a sense of danger."   },   {   "index": 13,   "name": "Hallway",   "description": "A narrow and winding hallway, with a sense of unease."   },   {   "index": 14,   "name": "Room with staircase leading down",   "description": "A dimly lit room with a staircase leading down into the depths of the dungeon, with a sense of danger and uncertainty."   },   {   "index": 15,   "name": "",   "description": ""   },   {   "index": 16,   "name": "Hallway",   "description": "A long and winding hallway, with doors leading off to either side."   },   {   "index": 17,   "name": "Hallway",   "description": "Another long and winding hallway, with doors leading off to either side."   },   {   "index": 18,   "name": "Room with staircase leading up",   "description": "A well-lit room with a staircase leading up to the surface, with a sense of hope and escape."   }]\n\n}'
        self.llm_util.set_story(self.story)
        result = self.llm_util.generate_dungeon_locations(zone_info="", locations= [], depth= 1, max_depth=2) # type LocationDescriptionResponse
        assert len(result.location_descriptions) == 19

        self.llm_util._world_building.io_util.response =' {   "locations": [   {   "index": 0,   "name": "Entrance to dungeon",   "description": "A dark and ominous entrance to the dungeon, with a sense of foreboding."   },   {   "index": 1,   "name": "Hallway",   "description": "A long and winding hallway, with doors leading off to either side."   },   {   "index": 2,   "name": "Hallway",   "description": "Another long and winding hallway, with doors leading off to either side."   },   {   "index": 3,   "name": "Hallway",   "description": "A narrow and dimly lit hallway, with a sense of claustrophobia."   },   {   "index": 4,   "name": "Hallway",   "description": "A wide and well-lit hallway, with a sense of grandeur."   },   {   "index": 5,   "name": "Hallway",   "description": "A twisting and turning hallway, with a sense of confusion."   },   {   "index": 6,   "name": "Hallway",   "description": "A long and straight hallway, with a sense of monotony."   },   {   "index": 7,   "name": "Hallway",   "description": "A dark and foreboding hallway, with a sense of danger."   },   {   "index": 8,   "name": "Hallway",   "description": "A narrow and winding hallway, with a sense of unease."   },   {   "index": 9,   "name": "Hallway",   "description": "A long and straight hallway, with a sense of tedium."   },   {   "index": 10,   "name": "Hallway",   "description": "A well-lit and grand hallway, with a sense of pride."   },   {   "index": 11,   "name": "Hallway",   "description": "A twisting and turning hallway, with a sense of mystery."   },   {   "index": 12,   "name": "Hallway",   "description": "A dark and foreboding hallway, with a sense of danger."   },   {   "index": 13,   "name": "Hallway",   "description": "A narrow and winding hallway, with a sense of unease."   },   {   "index": 14,   "name": "Room with staircase leading down",   "description": "A dimly lit room with a staircase leading down into the depths of the dungeon, with a sense of danger and uncertainty."   },   {   "index": 15,   "name": "",   "description": ""   },   {   "index": 16,   "name": "Hallway",   "description": "A long and winding hallway, with doors leading off to either side."   },   {   "index": 17,   "name": "Hallway",   "description": "Another long and winding hallway, with doors leading off to either side."   },   {   "index": 18,   "name": "Room with staircase leading up",   "description": "A well-lit room with a staircase leading up to the surface, with a sense of hope and escape."   }]\n\n}'

        result = self.llm_util.generate_dungeon_locations(zone_info="", locations= [], depth= 1, max_depth=2) # type LocationDescriptionResponse
        assert len(result.location_descriptions) == 19

        self.llm_util._world_building.io_util.response ='[   {   "index": 0,   "name": "Entrance to dungeon",   "description": "A dark and ominous entrance to the dungeon, with a sense of foreboding."   },   {   "index": 1,   "name": "Hallway",   "description": "A long and winding hallway, with doors leading off to either side."   },   {   "index": 2,   "name": "Hallway",   "description": "Another long and winding hallway, with doors leading off to either side."   },   {   "index": 3,   "name": "Hallway",   "description": "A narrow and dimly lit hallway, with a sense of claustrophobia."   },   {   "index": 4,   "name": "Hallway",   "description": "A wide and well-lit hallway, with a sense of grandeur."   },   {   "index": 5,   "name": "Hallway",   "description": "A twisting and turning hallway, with a sense of confusion."   },   {   "index": 6,   "name": "Hallway",   "description": "A long and straight hallway, with a sense of monotony."   },   {   "index": 7,   "name": "Hallway",   "description": "A dark and foreboding hallway, with a sense of danger."   },   {   "index": 8,   "name": "Hallway",   "description": "A narrow and winding hallway, with a sense of unease."   },   {   "index": 9,   "name": "Hallway",   "description": "A long and straight hallway, with a sense of tedium."   },   {   "index": 10,   "name": "Hallway",   "description": "A well-lit and grand hallway, with a sense of pride."   },   {   "index": 11,   "name": "Hallway",   "description": "A twisting and turning hallway, with a sense of mystery."   },   {   "index": 12,   "name": "Hallway",   "description": "A dark and foreboding hallway, with a sense of danger."   },   {   "index": 13,   "name": "Hallway",   "description": "A narrow and winding hallway, with a sense of unease."   },   {   "index": 14,   "name": "Room with staircase leading down",   "description": "A dimly lit room with a staircase leading down into the depths of the dungeon, with a sense of danger and uncertainty."   },   {   "index": 15,   "name": "",   "description": ""   },   {   "index": 16,   "name": "Hallway",   "description": "A long and winding hallway, with doors leading off to either side."   },   {   "index": 17,   "name": "Hallway",   "description": "Another long and winding hallway, with doors leading off to either side."   },   {   "index": 18,   "name": "Room with staircase leading up",   "description": "A well-lit room with a staircase leading up to the surface, with a sense of hope and escape."   }]'

        result = self.llm_util.generate_dungeon_locations(zone_info="", locations= [], depth= 1, max_depth=2) # type LocationDescriptionResponse
        assert len(result.location_descriptions) == 19



class TestQuestBuilding():

    llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil

    def test_generate_note_quest(self):
        self.llm_util._quest_building.io_util.response = '{"name": "Test Quest",  "reason": "A test quest", "target":"Arto", "type":"talk"}'
        world_generation_context = WorldGenerationContext(story_context='', story_type='', world_info='', world_mood=0)

        quest = self.llm_util._quest_building.generate_note_quest(context=world_generation_context, zone_info='')
        assert(quest.name == 'Test Quest')
        assert(quest.reason == 'A test quest')
        assert(quest.target == 'Arto')

        