from random import choice, randint, random, choices
from datetime import datetime
import pygame as pg
from pyGameWorld import PGWorld, ToolPicker, loadFromDict
from pyGameWorld.viewer import *
from pyGameWorld.jsrun import *
from pyGameWorld.helpers import *
import numpy as np
from copy import deepcopy

##############################################
#
# Algorithm
#
##############################################



##############################################

def generate_experiment_id():
    current_time = datetime.now()
    return current_time.strftime("%y%m%d_%H%M%S")

def draw_path(tp, path_dict, img_name, tool_pos=None):
    if not path_dict: return
    pg.display.set_mode((10,10))
    sc = drawPathSingleImageWithTools(tp, path_dict)
    if tool_pos:
        tool_pos = [tool_pos[0], 600-tool_pos[1]]
        pg.draw.circle(sc, (0,0,255), tool_pos, 5)
    img = sc.convert_alpha()
    pg.image.save(img, img_name)

def draw_multi_paths(world, path_set, img_name):
    if not path_set: return
    pg.display.set_mode((10,10))
    sc = drawMultiPathSingleImage(world, path_set)
    img = sc.convert_alpha()
    pg.image.save(img, img_name)

def set_prior_type(algorithm):
    if algorithm == 'SSUP':
        return get_prior_SSUP
    else:
        return get_prior_catapult

def print_stats(trial_stats):
    print('5: ', len([t for t in trial_stats if t <5])/len(trial_stats))
    for i in range(2,7):
        print(str(5*i)+':', len([str(5*j) for j in trial_stats if j <5*i])/len(trial_stats))

def get_prior_SSUP(tp, movable_objects): # NOTE - add tp
    obj = choice(movable_objects)
    BB = objectBoundingBox(tp.objects[obj])
    x = randint(BB[0][0]-20,BB[1][0]+20)
    range_y = choices([(0,BB[0][1]), (BB[1][1],600)], weights=[BB[0][1]-0, 600-BB[1][1]], k=1)[0]
    y = randint(range_y[0],range_y[1])
    return (x,y)

def get_prior_catapult(obj_dict):
    obj = choice(list(obj_dict.keys()))
    # if obj == 'Catapult':
    # prior of Catapult
    x0 = obj_dict['Catapult'].getPolys()[2][2][0]
    y0 = obj_dict['Catapult'].getPolys()[2][2][1]
    x = randint(x0-20, x0+20) # 
    y = randint(y0+20,600)
    # elif obj == 'Ball':
    #     # x = randint(112-20, 200+20)
    #     x = randint(90-20, 90+20)
    #     y = randint(0,600)

    return (x,y)

def calculate_reward(tp, path_dict, sample_obj):
    if not path_dict:
        return 0
    reward = -1
    for obj in path_dict:
        if obj == 'PLACED': continue
        if tp.objects[obj].color == (255, 0, 0, 255):
            dist0 = tp.world.distanceToGoalContainer((path_dict[obj][0][:2]))
            dist = tp.world.distanceToGoalContainer((path_dict[obj][-1][:2]))
            r = 1-(dist/dist0)
            if r > reward:
                reward = r
            # reward = -(dist/dist0-0.5)*2
    return reward

def normalize_pos(pos):
    return ((pos[0]-300)/100, (pos[1]-300)/100)

def scale_pos(pos):
    return ((pos[0]*100)+300, (pos[1]*100)+300)


def calculate_weights(policy_rewards, gaussian_policies):
    # weights=[sum(policy_rewards[i])/len(policy_rewards[i]) if policy_rewards[i] else 1 for i in gaussian_policies.keys()]
    # if min(weights) < 0:
    #     weights = [i - min(weights) for i in weights]

    weights = [sorted(policy_rewards).index(x)+1 for x in policy_rewards]
    return weights

def is_sublist(larger_list, sublist):
    # Lengths of the lists
    len_larger = len(larger_list)
    len_sublist = len(sublist)

    # A sublist cannot exist in a smaller list
    if len_sublist > len_larger:
        return False

    # Check each possible starting position in larger_list
    for start in range(len_larger - len_sublist + 1):
        # Check if the sublist matches at this position
        if larger_list[start:start + len_sublist] == sublist:
            return True

    # No match found
    return False

class ExtrinsicSampler():
    def __init__(self, btr, path_dict):
        self._btr = btr
        self.path_dict = path_dict
    
    def sample_pos(self, sample_obj):
        # TODO - sample from other counterfactual conditions
        rand_rad = random()*2*np.pi
        sample_pose = choice(self.path_dict[sample_obj]) # sample from intial path
        pos0, rot0 = sample_pose[0:2], sample_pose[2]
        rand_scale = randint(0,10)
        btr = deepcopy(self._btr)
        btr['world']['objects'][sample_obj]['position'] = (pos0[0] + rand_rad * rand_scale, pos0[1] + rand_rad * rand_scale)
        btr['world']['objects'][sample_obj]['rotation'] = (rot0 + (random()-0.5)*0.1)
        btr['world']['objects'][sample_obj]['color'] = (0, 0, 0) # fix pos
        return btr
    def sample_vel(self, sample_obj):
        rand_rad = random()*2*np.pi
        rand_scale = randint(1,50)*10
        velocity = [np.cos(rand_rad) * rand_scale,  np.sin(rand_rad) * rand_scale]
        btr = deepcopy(self._btr)
        btr['world']['objects'][sample_obj]['velocity'] = velocity
        return btr
    def sample_ang(self, sample_obj):
        rand_ang = randint(1,50)*10*2*np.pi
        btr = deepcopy(self._btr)
        btr['world']['objects'][sample_obj]['angular_velocity'] = rand_ang
        return btr

def node_match(node1, node2):
    print(node1, node2)
    return node1 == node2