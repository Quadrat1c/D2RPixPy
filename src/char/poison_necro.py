import keyboard
from utils.custom_mouse import mouse
from char import IChar
from template_finder import TemplateFinder
from pather import Pather, Location
from logger import Logger
from screen import grab, convert_abs_to_monitor, convert_screen_to_abs
from config import Config
from utils.misc import wait, rotate_vec, unit_vector
import random
from typing import Tuple
from pather import Location, Pather
import screen as screen
import numpy as np
import time
import os
from ui_manager import wait_for_screen_object, ScreenObjects

import cv2 #for Diablo
from item.pickit import PickIt #for Diablo

class Poison_Necro(IChar):
    def __init__(self, skill_hotkeys: dict, pather: Pather, pickit: PickIt):
        os.system('color')
        Logger.info("\033[94m<<Setting up Necro>>\033[0m")
        super().__init__(skill_hotkeys)
        self._pather = pather
        self._pickit = pickit #for Diablo
        self._picked_up_items = False #for Diablo
        #custom necro pathing for pindle
        self._pather.adapt_path((Location.A5_PINDLE_START, Location.A5_PINDLE_SAFE_DIST), [100,101])
        self._pather.adapt_path((Location.A5_PINDLE_SAFE_DIST, Location.A5_PINDLE_END), [104])
        #minor offsets to pindle fight locations
        self._pather.offset_node(102, [15, 0])
        self._pather.offset_node(103, [15, 0])
        self._pather.offset_node(101, [100,-5])
        
        #Diablo
        self._pather.offset_node(644, [150, -70])
        self._pather.offset_node(610620, [50, 50])
        self._pather.offset_node(631, [-50, 50])
        self._pather.offset_node(656, [-70, -50])

        self._shenk_dead = 0
        self._skeletons_count=0
        self._mages_count=0
        self._golem_count="none"
        self._revive_count=0


    def _check_shenk_death(self):
        ''' make sure shenk is dead checking for fireballs so we can exit combat sooner '''

        roi = [640,0,640,720]
        img = grab()

        template_match = TemplateFinder().search(
            ['SHENK_DEATH_1','SHENK_DEATH_2','SHENK_DEATH_3','SHENK_DEATH_4'],
            img,
            threshold=0.6,
            roi=roi,
            use_grayscale = False
        )
        if template_match.valid:
            self._shenk_dead=1
            Logger.info('\33[31m'+"Shenks Dead, looting..."+'\033[0m')
        else:
            return True

    def _count_revives(self):
        roi = [15,14,400,45]
        img = grab()
        max_rev = 13

        template_match = TemplateFinder().search(
            ['REV_BASE'],
            img,
            threshold=0.6,
            roi=roi
        )
        if template_match.valid:
            self._revive_count=max_rev
        else:
            self._revive_count=0
            return True

        for count in range(1,max_rev):
            rev_num = "REV_"+str(count)
            template_match = TemplateFinder().search(
                [rev_num],
                img,
                threshold=0.66,
                roi=roi,
                use_grayscale = False
            )
            if template_match.valid:
                self._revive_count=count


    def poison_nova(self, time_in_s: float):
        if not self._skill_hotkeys["poison_nova"]:
            raise ValueError("You did not set poison nova hotkey!")
        keyboard.send(self._skill_hotkeys["poison_nova"])
        wait(0.05, 0.1)
        start = time.time()
        while (time.time() - start) < time_in_s:
            wait(0.03, 0.04)
            mouse.press(button="right")
            wait(0.12, 0.2)
            mouse.release(button="right")    

    def _count_skeletons(self):
        roi = [15,14,400,45]
        img = grab()
        max_skeles = 13

        template_match = TemplateFinder().search(
            ['SKELE_BASE'],
            img,
            threshold=0.6,
            roi=roi
        )
        if template_match.valid:
            self._skeletons_count=max_skeles
        else:
            self._skeletons_count=0
            return True

        for count in range(1,max_skeles):
            skele_num = "SKELE_"+str(count)
            template_match = TemplateFinder().search(
                [skele_num],
                img,
                threshold=0.66,
                roi=roi,
                use_grayscale = False
            )
            if template_match.valid:
                self._skeletons_count=count

    def _count_gol(self):
        roi = [15,14,400,45]
        img = grab()

        template_match = TemplateFinder().search(
            ['CLAY'],
            img,
            threshold=0.6,
            roi=roi
        )
        if template_match.valid:
            self._golem_count="clay gol"
        else:
            self._golem_count="none"
            return True

    def _summon_count(self):
        ''' see how many summons and which golem are out '''
        self._count_skeletons()
        self._count_revives()
        self._count_gol()

    def _summon_stat(self):
        ''' print counts for summons '''
        Logger.info('\33[31m'+"Summon status | "+str(self._skeletons_count)+"skele | "+str(self._revive_count)+" rev | "+self._golem_count+" |"+'\033[0m')

    def _revive(self, cast_pos_abs: Tuple[float, float], spray: int = 10, cast_count: int=12):
        Logger.info('\033[94m'+"raise revive"+'\033[0m')
        keyboard.send(Config().char["stand_still"], do_release=False)
        for _ in range(cast_count):
            if self._skill_hotkeys["raise_revive"]:
                keyboard.send(self._skill_hotkeys["raise_revive"])
                #Logger.info("revive -> cast")
            x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
            y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
            cast_pos_monitor = screen.convert_abs_to_monitor((x, y))

            nx = cast_pos_monitor[0]
            ny = cast_pos_monitor[1]
            if(nx>1280):
                nx=1275
            if(ny>720):
                ny=715
            if(nx<0):
                nx=0
            if(ny<0):
                ny=0
            clamp = [nx,ny]

            mouse.move(*clamp)
            mouse.press(button="right")
            wait(0.075, 0.1)
            mouse.release(button="right")
        keyboard.send(Config().char["stand_still"], do_press=False)

    def _raise_skeleton(self, cast_pos_abs: Tuple[float, float], spray: int = 10, cast_count: int=16):
        Logger.info('\033[94m'+"raise skeleton"+'\033[0m')
        keyboard.send(Config().char["stand_still"], do_release=False)
        for _ in range(cast_count):
            if self._skill_hotkeys["raise_skeleton"]:
                keyboard.send(self._skill_hotkeys["raise_skeleton"])
                #Logger.info("raise skeleton -> cast")
            x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
            y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
            cast_pos_monitor = screen.convert_abs_to_monitor((x, y))

            nx = cast_pos_monitor[0]
            ny = cast_pos_monitor[1]
            if(nx>1280):
                nx=1279
            if(ny>720):
                ny=719
            if(nx<0):
                nx=0
            if(ny<0):
                ny=0
            clamp = [nx,ny]

            mouse.move(*clamp)
            mouse.press(button="right")
            wait(0.02, 0.05)
            mouse.release(button="right")
        keyboard.send(Config().char["stand_still"], do_press=False)

    def _raise_mage(self, cast_pos_abs: Tuple[float, float], spray: int = 10, cast_count: int=16):
        Logger.info('\033[94m'+"raise mage"+'\033[0m')
        keyboard.send(Config().char["stand_still"], do_release=False)
        for _ in range(cast_count):
            if self._skill_hotkeys["raise_mage"]:
                keyboard.send(self._skill_hotkeys["raise_mage"])
                #Logger.info("raise skeleton -> cast")
            x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
            y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
            cast_pos_monitor = screen.convert_abs_to_monitor((x, y))

            nx = cast_pos_monitor[0]
            ny = cast_pos_monitor[1]
            if(nx>1280):
                nx=1279
            if(ny>720):
                ny=719
            if(nx<0):
                nx=0
            if(ny<0):
                ny=0
            clamp = [nx,ny]

            mouse.move(*clamp)
            mouse.press(button="right")
            wait(0.02, 0.05)
            mouse.release(button="right")
        keyboard.send(Config().char["stand_still"], do_press=False)


    def pre_buff(self):
        #necro pre_buff
        self.bone_armor()
        #only CTA if pre trav
        if Config().char["cta_available"]:
            self._pre_buff_cta()
        if self._shenk_dead==1:
            Logger.info("trav buff?")
            #self._heart_of_wolverine()
        Logger.info("prebuff/cta")


    def _heart_of_wolverine(self):
        Logger.info('\033[94m'+"buff ~> heart_of_wolverine"+'\033[0m')
        keyboard.send(self._skill_hotkeys["heart_of_wolverine"])
        wait(0.05, 0.2)
        mouse.click(button="right")
        wait(self._cast_duration)

    def _clay_golem(self):
        Logger.info('\033[94m'+"cast ~> clay golem"+'\033[0m')
        keyboard.send(self._skill_hotkeys["clay_golem"])
        wait(0.05, 0.2)
        mouse.click(button="right")
        wait(self._cast_duration)


    def bone_armor(self):
        if self._skill_hotkeys["bone_armor"]:
            keyboard.send(self._skill_hotkeys["bone_armor"])
            wait(0.04, 0.1)
            mouse.click(button="right")
            wait(self._cast_duration)
        if self._skill_hotkeys["clay_golem"]:
            keyboard.send(self._skill_hotkeys["clay_golem"])
            wait(0.04, 0.1)
            mouse.click(button="right")
            wait(self._cast_duration)

    def _bone_armor(self):
        if self._skill_hotkeys["bone_armor"]:
            keyboard.send(self._skill_hotkeys["bone_armor"])
            wait(0.04, 0.1)
            mouse.click(button="right")
            wait(self._cast_duration)



    def _left_attack(self, cast_pos_abs: Tuple[float, float], spray: int = 10):
        keyboard.send(Config().char["stand_still"], do_release=False)
        if self._skill_hotkeys["skill_left"]:
            keyboard.send(self._skill_hotkeys["skill_left"])
        for _ in range(10):
            x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
            y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
            cast_pos_monitor = screen.convert_abs_to_monitor((x, y))
            mouse.move(*cast_pos_monitor)
            mouse.press(button="left")
            wait(0.25, 0.3)
            mouse.release(button="left")

        keyboard.send(Config().char["stand_still"], do_press=False)

    def _left_attack_single(self, cast_pos_abs: Tuple[float, float], spray: int = 10, cast_count: int=6):
        keyboard.send(Config().char["stand_still"], do_release=False)
        if self._skill_hotkeys["skill_left"]:
            keyboard.send(self._skill_hotkeys["skill_left"])
        for _ in range(cast_count):
            x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
            y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
            cast_pos_monitor = screen.convert_abs_to_monitor((x, y))
            mouse.move(*cast_pos_monitor)
            mouse.press(button="left")
            wait(0.25, 0.3)
            mouse.release(button="left")

        keyboard.send(Config().char["stand_still"], do_press=False)

    def _amp_dmg(self, cast_pos_abs: Tuple[float, float], spray: float = 10):
        if self._skill_hotkeys["amp_dmg"]:
            keyboard.send(self._skill_hotkeys["amp_dmg"])

        x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
        y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
        cast_pos_monitor = screen.convert_abs_to_monitor(x, y)
        mouse.move(*cast_pos_monitor)
        mouse.press(button="right")
        wait(0.25, 0.35)
        mouse.release(button="right")

    def _lower_res(self, cast_pos_abs: Tuple[float, float], spray: float = 10):
        if self._skill_hotkeys["lower_res"]:
            keyboard.send(self._skill_hotkeys["lower_res"])

        x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
        y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
        cast_pos_monitor = screen.convert_abs_to_monitor(x, y)
        mouse.move(*cast_pos_monitor)
        mouse.press(button="right")
        wait(0.25, 0.35)
        mouse.release(button="right")        

    def _corpse_explosion(self, cast_pos_abs: Tuple[float, float], spray: int = 10,cast_count: int = 8):
        keyboard.send(Config().char["stand_still"], do_release=False)
        Logger.info('\033[93m'+"corpse explosion~> random cast"+'\033[0m')
        for _ in range(cast_count):
            if self._skill_hotkeys["corpse_explosion"]:
                keyboard.send(self._skill_hotkeys["corpse_explosion"])
                x = cast_pos_abs[0] + (random.random() * 2*spray - spray)
                y = cast_pos_abs[1] + (random.random() * 2*spray - spray)
                cast_pos_monitor = screen.convert_abs_to_monitor(x, y)
                mouse.move(*cast_pos_monitor)
                mouse.press(button="right")
                wait(0.075, 0.1)
                mouse.release(button="right")
        keyboard.send(Config().char["stand_still"], do_press=False)


    def _lerp(self,a: float,b: float, f:float):
        return a + f * (b - a)

    def _cast_circle(self, cast_dir: Tuple[float,float],cast_start_angle: float=0.0, cast_end_angle: float=90.0,cast_div: int = 10,cast_v_div: int=4,cast_spell: str='raise_skeleton',delay: float=1.0,offset: float=1.0):
        Logger.info('\033[93m'+"circle cast ~>"+cast_spell+'\033[0m')
        keyboard.send(Config().char["stand_still"], do_release=False)
        keyboard.send(self._skill_hotkeys[cast_spell])
        mouse.press(button="right")

        for i in range(cast_div):
            angle = self._lerp(cast_start_angle,cast_end_angle,float(i)/cast_div)
            target = unit_vector(rotate_vec(cast_dir, angle))
            #Logger.info("current angle ~> "+str(angle))
            for j in range(cast_v_div):
                circle_pos_screen = self._pather._adjust_abs_range_to_screen((target*120.0*float(j+1.0))*offset)
                circle_pos_monitor = screen.convert_abs_to_monitor(circle_pos_screen)
                mouse.move(*circle_pos_monitor,delay_factor=[0.3*delay, .6*delay])


                #Logger.info("circle move")
        mouse.release(button="right")
        keyboard.send(Config().char["stand_still"], do_press=False)

    def Chaos_Attack_Basic(self):
        rx = random.uniform(10, 75)
        ry = -abs(rx)

        pos_m = screen.convert_abs_to_monitor((ry, 0))
        mouse.move(*pos_m, randomize=80, delay_factor=[0.2, 0.3])
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        self.poison_nova(2.0)

        pos_m = screen.convert_abs_to_monitor((0, rx))
        mouse.move(*pos_m, randomize=80, delay_factor=[0.2, 0.3])
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        self.poison_nova(2.0)
        wait(0.2)
        self.bone_armor()
        

    def Summon_Check(self):
        pickx = random.uniform(1, 3)
        rx = random.uniform(0, 10)
        ry = random.uniform(0, -10)
        
        if pickx == 1:
            self._raise_skeleton([0,rx],180,cast_count=2)
            self._raise_skeleton([0,ry],180,cast_count=1)
        if pickx == 2:
            self._raise_mage([0,rx],180,cast_count=1)
            self._raise_mage([0,ry],180,cast_count=2)
        if pickx == 3:
            self._revive([0,rx],180,cast_count=2)
            self._revive([0,ry],180,cast_count=1)
        
        if self._golem_count == "none":
            self._clay_golem()

        """
        for _ in range(2):
            self._summon_count()
            if self._revive_count < 18:
                rx = random.uniform(0, 10)
                ry = random.uniform(0, -10)
                self._revive([0,rx],180,cast_count=2)
                self._revive([0,ry],180,cast_count=2)
            if self._skeletons_count < 14:
                rx = random.uniform(0, 10)
                ry = random.uniform(0, -10)
                self._raise_skeleton([0,rx],180,cast_count=2)
                self._raise_skeleton([0,ry],180,cast_count=2)
            if self._mages_count < 14:
                rx = random.uniform(0, 10)
                ry = random.uniform(0, -10)
                self._raise_mage([0,rx],180,cast_count=2)
                self._raise_mage([0,ry],180,cast_count=2)
        if self._golem_count == "none":
            self._clay_golem()
        self._summon_count()
        self._summon_stat()
        """

    def kill_pindle(self) -> bool:
        pos_m = screen.convert_abs_to_monitor((0, 30))
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        self.poison_nova(3.0)
        pos_m = screen.convert_abs_to_monitor((0, -50))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        pos_m = screen.convert_abs_to_monitor((50, 0))
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=120,cast_div=5,cast_v_div=2,cast_spell='corpse_explosion',delay=1.1,offset=1.8)
        self.poison_nova(3.0)
        return True

    def kill_eldritch(self) -> bool:
        pos_m = screen.convert_abs_to_monitor((0, -100))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        #self.bone_armor()
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        self.poison_nova(2.0)
        self._summon_stat()
        # move a bit back
        pos_m = screen.convert_abs_to_monitor((0, 50))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self.poison_nova(2.0)
        self._pather.traverse_nodes((Location.A5_ELDRITCH_SAFE_DIST, Location.A5_ELDRITCH_END), self, time_out=0.6, force_tp=True)
        pos_m = screen.convert_abs_to_monitor((0, 170))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=8,cast_v_div=4,cast_spell='raise_revive',delay=1.2,offset=.8)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=720,cast_div=8,cast_v_div=4,cast_spell='raise_skeleton',delay=1.1,offset=.8)
        pos_m = screen.convert_abs_to_monitor((0, -50))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=720,cast_div=8,cast_v_div=4,cast_spell='raise_mage',delay=1.1,offset=1.0)
        pos_m = screen.convert_abs_to_monitor((-75, 0))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=720,cast_div=8,cast_v_div=4,cast_spell='raise_skeleton',delay=1.1,offset=.5)
        self._summon_count()
        self._summon_stat()
        self.bone_armor()

        self._pather.traverse_nodes((Location.A5_ELDRITCH_SAFE_DIST, Location.A5_ELDRITCH_END), self, time_out=0.6, force_tp=True)
        return True


    def kill_shenk(self) -> bool:
        self._pather.traverse_nodes((Location.A5_SHENK_SAFE_DIST, Location.A5_SHENK_END), self, time_out=1.0)
        #pos_m = self._screen.convert_abs_to_monitor((50, 0))
        #self.walk(pos_m, force_move=True)
        #self.bone_armor()
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        self.poison_nova(3.0)
        pos_m = screen.convert_abs_to_monitor((0, -50))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=720,cast_div=10,cast_v_div=4,cast_spell='raise_mage',delay=1.1,offset=.8)
        pos_m = screen.convert_abs_to_monitor((50, 0))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=720,cast_div=10,cast_v_div=4,cast_spell='raise_revive',delay=1.1,offset=.8)
        pos_m = screen.convert_abs_to_monitor((-20, -20))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=10,cast_v_div=4,cast_spell='raise_skeleton',delay=1.1,offset=.8)
        self._summon_count()
        self.bone_armor()
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=2,cast_v_div=1,cast_spell='corpse_explosion',delay=3.0,offset=1.8)
        return True


    def kill_council(self) -> bool:
        pos_m = screen.convert_abs_to_monitor((0, -200))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._pather.traverse_nodes([229], self, time_out=2.5, force_tp=True, use_tp_charge=True)       
        pos_m = screen.convert_abs_to_monitor((50, 0))
        self.walk(pos_m, force_move=True)
        #self._lower_res((-50, 0), spray=10)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)  
        self.poison_nova(2.0)
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=9,cast_v_div=3,cast_spell='raise_skeleton',delay=1.2,offset=.8)
        pos_m = screen.convert_abs_to_monitor((200, 50))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        pos_m = screen.convert_abs_to_monitor((30, -50))
        self.walk(pos_m, force_move=True)
        self.poison_nova(2.0)
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=120,cast_div=2,cast_v_div=1,cast_spell='corpse_explosion',delay=3.0,offset=1.8)
        #wait(self._cast_duration, self._cast_duration +.2)
        pos_m = screen.convert_abs_to_monitor((-200, 200))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        pos_m = screen.convert_abs_to_monitor((-100, 200))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._pather.traverse_nodes([226], self, time_out=2.5, force_tp=True, use_tp_charge=True)
        pos_m = screen.convert_abs_to_monitor((0, 30))
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        wait(0.5)
        self.poison_nova(4.0)
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=120,cast_div=2,cast_v_div=1,cast_spell='corpse_explosion',delay=3.0,offset=1.8)
        #wait(self._cast_duration, self._cast_duration +.2)
        #self.poison_nova(2.0)
        pos_m = screen.convert_abs_to_monitor((50, 0))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=120,cast_div=5,cast_v_div=2,cast_spell='corpse_explosion',delay=0.5,offset=1.8)
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=9,cast_v_div=3,cast_spell='raise_skeleton',delay=1.2,offset=.8)
        #self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=9,cast_v_div=3,cast_spell='raise_mage',delay=1.2,offset=.8)
        pos_m = screen.convert_abs_to_monitor((-200, -200))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._pather.traverse_nodes([229], self, time_out=2.5, force_tp=True, use_tp_charge=True)
        pos_m = screen.convert_abs_to_monitor((20, -50))
        self.walk(pos_m, force_move=True)
        self.poison_nova(2.0)
        pos_m = screen.convert_abs_to_monitor((50, 0))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=120,cast_div=5,cast_v_div=2,cast_spell='corpse_explosion',delay=3.0,offset=1.8)
        pos_m = screen.convert_abs_to_monitor((-30, -20))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=10,cast_v_div=4,cast_spell='raise_skeleton',delay=1.2,offset=.8)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=10,cast_v_div=4,cast_spell='raise_mage',delay=1.2,offset=.8)
        return True

    def kill_nihlathak(self, end_nodes: list[int]) -> bool:
        # Move close to nihlathak
        self._pather.traverse_nodes(end_nodes, self, time_out=0.8, do_pre_move=True)
        pos_m = screen.convert_abs_to_monitor((20, 20))
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        self.poison_nova(3.0)
        pos_m = screen.convert_abs_to_monitor((50, 0))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=7200,cast_div=2,cast_v_div=2,cast_spell='corpse_explosion',delay=3.0,offset=1.8)
        wait(self._cast_duration, self._cast_duration +.2)
        self.poison_nova(3.0)
        return True 

    def kill_summoner(self) -> bool:
        # Attack
        pos_m = screen.convert_abs_to_monitor((0, 30))
        self.walk(pos_m, force_move=True)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=4,cast_v_div=3,cast_spell='lower_res',delay=1.0)
        wait(0.5)
        self.poison_nova(3.0)
        pos_m = screen.convert_abs_to_monitor((50, 0))
        #self.pre_move()
        self.move(pos_m, force_move=True)
        wait(self._cast_duration, self._cast_duration + 0.2)
        self._cast_circle(cast_dir=[-1,1],cast_start_angle=0,cast_end_angle=360,cast_div=10,cast_v_div=4,cast_spell='raise_mage',delay=1.2,offset=.8)
        return True

    ########################################################################################
     # Chaos Sanctuary, Trash, Seal Bosses (a = Vizier, b = De Seis, c = Infector) & Diablo #
     ########################################################################################

    def kill_cs_trash(self, location:str) -> bool:

        ###########
        # SEALDANCE
        ###########

        if location == "sealdance": #if seal opening fails & trash needs to be cleared -> used at ANY seal
            ### APPROACH
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        ################
        # CLEAR CS TRASH
        ################

        elif location == "rof_01": #node 603 - outside CS in ROF
            ### APPROACH ###
            if not self._pather.traverse_nodes([603], self, time_out=3): return False #calibrate after static path
            pos_m = convert_abs_to_monitor((0, 0))
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            #mouse.move(*pos_m, randomize=80, delay_factor=[0.5, 0.7])
            self.Chaos_Attack_Basic()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            ### SUMMON ###
            self.Summon_Check()

            
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([603], self): return False #calibrate after looting


        elif location == "rof_02": #node 604 - inside ROF
            ### APPROACH ###
            if not self._pather.traverse_nodes([604], self, time_out=3): return False  #threshold=0.8 (ex 601)
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        elif location == "entrance_hall_01": ##static_path "diablo_entrance_hall_1", node 677, CS Entrance Hall1
            ### APPROACH ###
            self._pather.traverse_nodes_fixed("diablo_entrance_hall_1", self) # 604 -> 671 Hall1
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        elif location == "entrance_hall_02":  #node 670,671, CS Entrance Hall1, CS Entrance Hall1
            ### APPROACH ###
            if not self._pather.traverse_nodes([670], self): return False # pull top mobs 672 to bottom 670
            self._pather.traverse_nodes_fixed("diablo_entrance_1_670_672", self) # 604 -> 671 Hall1
            if not self._pather.traverse_nodes([670], self): return False # pull top mobs 672 to bottom 670
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            #Move to Layout Check
            if not self._pather.traverse_nodes([671], self): return False # calibrate before static path
            self._pather.traverse_nodes_fixed("diablo_entrance_hall_2", self) # 671 -> LC Hall2



        # TRASH LAYOUT A

        elif location == "entrance1_01": #static_path "diablo_entrance_hall_2", Hall1 (before layout check)
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([673], self): return False # , time_out=3): # Re-adjust itself and continues to attack

        elif location == "entrance1_02": #node 673
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self._pather.traverse_nodes_fixed("diablo_entrance_1_1", self) # Moves char to postion close to node 674 continues to attack
            if not self._pather.traverse_nodes([674], self): return False#, time_out=3)

        elif location == "entrance1_03": #node 674
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([675], self): return False#, time_out=3) # Re-adjust itself
            self._pather.traverse_nodes_fixed("diablo_entrance_1_1", self) #static path to get to be able to spot 676
            if not self._pather.traverse_nodes([676], self): return False#, time_out=3)

        elif location == "entrance1_04": #node 676- Hall3
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        # TRASH LAYOUT B

        elif location == "entrance2_01": #static_path "diablo_entrance_hall_2"
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self.pre_buff()

        elif location == "entrance2_02": #node 682
            ### APPROACH ###
            #if not self._pather.traverse_nodes([682], self): return False # , time_out=3):
            self._pather.traverse_nodes_fixed("diablo_trash_b_hall2_605_right", self) #pull mobs from the right
            wait (0.2, 0.5)
            if not self._pather.traverse_nodes([605], self): return False#, time_out=3)
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self.pre_buff()

        elif location == "entrance2_03": #node 683
            ### APPROACH ###
            #if not self._pather.traverse_nodes([682], self): return False # , time_out=3):
            #self._pather.traverse_nodes_fixed("diablo_entrance2_1", self)
            #if not self._pather.traverse_nodes([683], self): return False # , time_out=3):
            self._pather.traverse_nodes_fixed("diablo_trash_b_hall2_605_top1", self) #pull mobs from top
            wait (0.2, 0.5)
            self._pather.traverse_nodes_fixed("diablo_trash_b_hall2_605_top2", self) #pull mobs from top
            if not self._pather.traverse_nodes([605], self): return False#, time_out=3)
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self.pre_buff()

        elif location == "entrance2_04": #node 686 - Hall3
            ### APPROACH ###
            if not self._pather.traverse_nodes([605], self): return False#, time_out=3)
            #if not self._pather.traverse_nodes([683,684], self): return False#, time_out=3)
            #self._pather.traverse_nodes_fixed("diablo_entrance2_2", self)
            #if not self._pather.traverse_nodes([685,686], self): return False#, time_out=3)
            self._pather.traverse_nodes_fixed("diablo_trash_b_hall2_605_hall3", self)
            if not self._pather.traverse_nodes([609], self): return False#, time_out=3)
            self._pather.traverse_nodes_fixed("diablo_trash_b_hall3_pull_609", self)
            if not self._pather.traverse_nodes([609], self): return False#, time_out=3)
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([609], self): return False#, time_out=3)
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([609], self): return False#, time_out=3)
            self.pre_buff()

        ####################
        # PENT TRASH TO SEAL
        ####################

        elif location == "dia_trash_a": #trash before between Pentagramm and Seal A Layoutcheck
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self.pre_buff()

        elif location == "dia_trash_b": #trash before between Pentagramm and Seal B Layoutcheck
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self.pre_buff()

        elif location == "dia_trash_c": ##trash before between Pentagramm and Seal C Layoutcheck
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            self.pre_buff()

        ###############
        # LAYOUT CHECKS
        ###############

        elif location == "layoutcheck_a": #layout check seal A, node 619 A1-L, node 620 A2-Y
            ### APPROACH ###
            ### ATTACK ###
            Logger.debug("No attack choreography available in hammerdin.py for this node " + location + " - skipping to shorten run.")

        elif location == "layoutcheck_b": #layout check seal B, node 634 B1-S, node 649 B2-U
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        elif location == "layoutcheck_c": #layout check seal C, node 656 C1-F, node 664 C2-G
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        ##################
        # PENT BEFORE SEAL
        ##################

        elif location == "pent_before_a": #node 602, pentagram, before CTA buff & depature to layout check - not needed when trash is skipped & seals run in right order
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            Logger.debug("No attack choreography available in hammerdin.py for this node " + location + " - skipping to shorten run.")

        elif location == "pent_before_b": #node 602, pentagram, before CTA buff & depature to layout check
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        elif location == "pent_before_c": #node 602, pentagram, before CTA buff & depature to layout check
            ### APPROACH ###
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        ###########
        # SEAL A1-L
        ###########

        elif location == "A1-L_01":  #node 611 seal layout A1-L: safe_dist
            ### APPROACH ###
            if not self._pather.traverse_nodes([611], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            # we loot at boss

        elif location == "A1-L_02":  #node 612 seal layout A1-L: center
            ### APPROACH ###
            if not self._pather.traverse_nodes([612], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            # we loot at boss

        elif location == "A1-L_03":  #node 613 seal layout A1-L: fake_seal
            ### APPROACH ###
            if not self._pather.traverse_nodes([613], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        elif location == "A1-L_seal1":  #node 613 seal layout A1-L: fake_seal
            ### APPROACH ###
            #self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([614], self): return False
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            # we loot at boss

        elif location == "A1-L_seal2":  #node 614 seal layout A1-L: boss_seal
            ### APPROACH ###
            if not self._pather.traverse_nodes([613, 615], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            # we loot at boss

        ###########
        # SEAL A2-Y
        ###########

        elif location == "A2-Y_01":  #node 622 seal layout A2-Y: safe_dist
            ### APPROACH ###
            if not self._pather.traverse_nodes_fixed("dia_a2y_hop_622", self): return False
            Logger.info("A2-Y: Hop!")
            #if not self._pather.traverse_nodes([622], self): return False # , time_out=3):
            if not self._pather.traverse_nodes([622], self): return False
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            # we loot at boss

        elif location == "A2-Y_02":  #node 623 seal layout A2-Y: center
            ### APPROACH ###
            # if not self._pather.traverse_nodes([623,624], self): return False #
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            # we loot at boss

        elif location == "A2-Y_03": #skipped
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "A2-Y_seal1":  #node 625 seal layout A2-Y: fake seal
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            if not self._pather.traverse_nodes([625], self): return False # , time_out=3):

        elif location == "A2-Y_seal2":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            self._pather.traverse_nodes_fixed("dia_a2y_sealfake_sealboss", self) #instead of traversing node 626 which causes issues

        ###########
        # SEAL B1-S
        ###########

        elif location == "B1-S_01":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "B1-S_02":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "B1-S_03":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "B1-S_seal2": #B only has 1 seal, which is the boss seal = seal2
            ### APPROACH ###
            if not self._pather.traverse_nodes([634], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)


        ###########
        # SEAL B2-U
        ###########

        elif location == "B2-U_01":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "B2-U_02":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "B2-U_03":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "B2-U_seal2": #B only has 1 seal, which is the boss seal = seal2
            ### APPROACH ###
            self._pather.traverse_nodes_fixed("dia_b2u_bold_seal", self)
            if not self._pather.traverse_nodes([644], self): return False # , time_out=3):
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            self.Chaos_Attack_Basic()


        ###########
        # SEAL C1-F
        ###########

        elif location == "C1-F_01":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "C1-F_02":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "C1-F_03":
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "C1-F_seal1":
            ### APPROACH ###
            wait(0.1,0.3)
            self._pather.traverse_nodes_fixed("dia_c1f_hop_fakeseal", self)
            wait(0.1,0.3)
            if not self._pather.traverse_nodes([655], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([655], self): return False # , time_out=3):

        elif location == "C1-F_seal2":
            ### APPROACH ###
            self._pather.traverse_nodes_fixed("dia_c1f_654_651", self)
            if not self._pather.traverse_nodes([652], self): return False # , time_out=3):
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([652], self): return False # , time_out=3):

        ###########
        # SEAL C2-G
        ###########

        elif location == "C2-G_01": #skipped
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "C2-G_02": #skipped
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "C2-G_03": #skipped
            ### APPROACH ###
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")

        elif location == "C2-G_seal1":
            ### APPROACH ###
            #if not self._pather.traverse_nodes([663, 662], self): return False # , time_out=3): #caused 7% failed runs, replaced by static path.
            self._pather.traverse_nodes_fixed("dia_c2g_lc_661", self)
            ### ATTACK ###
            ### LOOT ###
            # we loot at boss
            Logger.debug("No attack choreography available in poison_necro.py for this node " + location + " - skipping to shorten run.")
            """
            pos_m = convert_abs_to_monitor((0, 0))
            mouse.move(*pos_m, randomize=80, delay_factor=[0.5, 0.7])
            self._move_and_attack((30, 15), Config().char["atk_len_cs_trashmobs"] * 0.5)
            self._cast_hammers(0.75, "redemption")
            self._move_and_attack((-30, -15), Config().char["atk_len_cs_trashmobs"] * 0.5)
            if self._skill_hotkeys["cleansing"]:
                keyboard.send(self._skill_hotkeys["cleansing"])
                wait(0.1, 0.2)
            if self._skill_hotkeys["redemption"]:
                keyboard.send(self._skill_hotkeys["redemption"])
                wait(0.3, 0.6)
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if self._skill_hotkeys["redemption"]:
                keyboard.send(self._skill_hotkeys["redemption"])
                wait(0.3, 0.6)
            """

        elif location == "C2-G_seal2":
            ### APPROACH ###
            # Killing infector here, because for C2G its the only seal where a bossfight occures BETWEEN opening seals
            seal_layout="C2-G"
            self._pather.traverse_nodes_fixed("dia_c2g_663", self)
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([664, 665], self): return False # , time_out=3):

        else:
            ### APPROACH ###
            Logger.debug("I have no location argument given for kill_cs_trash(" + location + "), should not happen. Throwing some random hammers")
            ### ATTACK ###
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
        return True



    def kill_vizier(self, seal_layout:str) -> bool:
        if seal_layout == "A1-L":
            ### APPROACH ###
            if not self._pather.traverse_nodes([612], self): return False # , time_out=3):
            ### ATTACK ###
            Logger.debug(seal_layout + ": Attacking Vizier at position 1/2")
            self.Chaos_Attack_Basic()
            self.Chaos_Attack_Basic()
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([612], self): return False # , time_out=3):
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([612], self): return False # , time_out=3): # recalibrate after loot

        elif seal_layout == "A2-Y":
            ### APPROACH ###
            if not self._pather.traverse_nodes([627, 622], self): return False # , time_out=3):
            ### ATTACK ###
            Logger.debug(seal_layout + ": Attacking Vizier at position 1/2")
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking Vizier at position 2/2")
            self._pather.traverse_nodes([623], self, time_out=3)
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking Vizier at position 3/3")
            if not self._pather.traverse_nodes([624], self): return False
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([624], self): return False
            if not self._pather.traverse_nodes_fixed("dia_a2y_hop_622", self): return False
            Logger.info(seal_layout + ": Hop!")
            if not self._pather.traverse_nodes([622], self): return False #, time_out=3):
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([622], self): return False # , time_out=3): #recalibrate after loot

        else:
            Logger.debug(seal_layout + ": Invalid location for kill_deseis("+ seal_layout +"), should not happen.")
            return False
        return True



    def kill_deseis(self, seal_layout:str) -> bool:
        if seal_layout == "B1-S":
            ### APPROACH ###
            self._pather.traverse_nodes_fixed("dia_b1s_seal_deseis", self) # quite aggressive path, but has high possibility of directly killing De Seis with first hammers, for 50% of his spawn locations
            nodes1 = [632]
            nodes2 = [631]
            nodes3 = [632]
            ### ATTACK ###
            Logger.debug(seal_layout + ": Attacking De Seis at position 1/4")
            pos_m = convert_abs_to_monitor((0, 0))
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking De Seis at position 2/4")
            self._pather.traverse_nodes(nodes1, self, time_out=3)
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking De Seis at position 3/4")
            self._pather.traverse_nodes(nodes2, self, time_out=3)
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking De Seis at position 4/4")
            self._pather.traverse_nodes(nodes3, self, time_out=3)
            self.Chaos_Attack_Basic()
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            #if Config().general["info_screenshots"]: cv2.imwrite(f"./info_screenshots/info_check_deseis_dead" + seal_layout + "_" + time.strftime("%Y%m%d_%H%M%S") + ".png", grab())
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)

        elif seal_layout == "B2-U":
            ### APPROACH ###
            self._pather.traverse_nodes_fixed("dia_b2u_644_646", self) # We try to breaking line of sight, sometimes makes De Seis walk into the hammercloud. A better attack sequence here could make sense.
            #self._pather.traverse_nodes_fixed("dia_b2u_seal_deseis", self) # We try to breaking line of sight, sometimes makes De Seis walk into the hammercloud. A better attack sequence here could make sense.
            nodes1 = [640]
            nodes2 = [646]
            nodes3 = [641]
            ### ATTACK ###
            Logger.debug(seal_layout + ": Attacking De Seis at position 1/4")
            pos_m = convert_abs_to_monitor((0, 0))
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking De Seis at position 2/4")
            self._pather.traverse_nodes(nodes1, self, time_out=3)
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking De Seis at position 3/4")
            self._pather.traverse_nodes(nodes2, self, time_out=3)
            self.Chaos_Attack_Basic()
            Logger.debug(seal_layout + ": Attacking De Seis at position 4/4")
            self._pather.traverse_nodes(nodes3, self, time_out=3)
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            #if Config().general["info_screenshots"]: cv2.imwrite(f"./info_screenshots/info_check_deseis_dead" + seal_layout + "_" + time.strftime("%Y%m%d_%H%M%S") + ".png", grab())
            ### LOOT ###
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([641], self): return False # , time_out=3):
            if not self._pather.traverse_nodes([646], self): return False # , time_out=3):
            self._picked_up_items |= self._pickit.pick_up_items(self)
            if not self._pather.traverse_nodes([646], self): return False # , time_out=3):
            if not self._pather.traverse_nodes([640], self): return False # , time_out=3):
            self._picked_up_items |= self._pickit.pick_up_items(self)

        else:
            Logger.debug(seal_layout + ": Invalid location for kill_deseis("+ seal_layout +"), should not happen.")
            return False
        return True



    def kill_infector(self, seal_layout:str) -> bool:
        if seal_layout == "C1-F":
            ### APPROACH ###
            self._pather.traverse_nodes_fixed("dia_c1f_652", self)
            ### ATTACK ###
            pos_m = convert_abs_to_monitor((0, 0))
            self.Chaos_Attack_Basic()
            ### SUMMON ###
            self.Summon_Check()
            ### LOOT ###
            #self._picked_up_items |= self._pickit.pick_up_items(self)

        elif seal_layout == "C2-G":
            # NOT killing infector here, because for C2G its the only seal where a bossfight occures BETWEEN opening seals his attack sequence can be found in C2-G_seal2
            Logger.debug(seal_layout + ": No need for attacking Infector at position 1/1 - he was killed during clearing the seal")

        else:
            Logger.debug(seal_layout + ": Invalid location for kill_infector("+ seal_layout +"), should not happen.")
            return False
        return True



    def kill_diablo(self) -> bool:
        ### APPROACH ###
        ### ATTACK ###
        Logger.debug("No Attack for Diablo in poison_necro.py")
        """
        pos_m = convert_abs_to_monitor((0, 0))
        mouse.move(*pos_m, randomize=80, delay_factor=[0.5, 0.7])
        Logger.debug("Attacking Diablo at position 1/1")
        self._cast_hammers(Config().char["atk_len_diablo"])
        self._cast_hammers(0.8, "redemption")
        self._move_and_attack((60, 30), Config().char["atk_len_diablo"])
        self._cast_hammers(0.8, "redemption")
        self._move_and_attack((-60, -30), Config().char["atk_len_diablo"])
        wait(0.1, 0.15)
        self._cast_hammers(1.2, "redemption")
        ### LOOT ###
        self._picked_up_items |= self._pickit.pick_up_items(self)
        """
        return True      


if __name__ == "__main__":
    import os
    import keyboard
    keyboard.add_hotkey('f12', lambda: Logger.info('Force Exit (f12)') or os._exit(1))
    keyboard.wait("f11")
    from config import Config
    from char import Necro
    pather = Pather()
    char = Necro(Config().necro, Config().char, pather)
