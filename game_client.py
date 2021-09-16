# encoding: utf-8

import socket
import threading
import sys
import time
import logging
# pip install panda3d==1.10.6
# import panda3dffff
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, Vec3, CollisionTraverser, CollisionHandlerPusher
from FreedomCampaignGame.comm_with_server import ClientLogObject, CommWithServer
from FreedomCampaignGame.game_role import Player, Enemy, TrapEnemy
from FreedomCampaignGame.game_map import GameMap

client_logger = ClientLogObject().client_logger

class Game(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        properties = WindowProperties()
        properties.setSize(1333, 960)
        self.win.requestProperties(properties)
        # 禁用默认的相机控制
        self.disableMouse()
        # 控制相机的位置和角度，相当于模型不变，我们自己变位置和角度来看
        #self.camera.setPos(0, -20, 20)
        # 角度设置，"H"、"P"、"R"
        self.camera.setP(-40)

        GameMap(self.render, self.loader.load_model)

        # 我们可以只使用一个遍历器，并让它在每次更新时检查冲突。在这种情况下，
        # ShowBase类提供了一个默认变量“ cTrav”：如果您为此变量分配了一个新的遍历器，Panda将自动为您更新。
        self.cTrav = CollisionTraverser()
        # CollisionHandlerPusher” 碰撞推送处理器 可防止指定的实体对象与其他实体对象相交。
        self.pusher = CollisionHandlerPusher()
        # 将碰撞响应设置为仅限于水平碰撞(即二维的物体)
        # self.pusher.setHorizontal(True)
        # 碰撞机需要在这里加，在Role类里加会导致没有碰撞作用，暂时还不知道为什么
        self.player = Player(base=base, load_model_fun=self.loader.load_model, render=self.render, role_name='player')
        self.pusher.add_collider(self.player.collider, self.player)
        self.cTrav.add_collider(self.player.collider, self.pusher)
        #self.cTrav.add_collider(self.player.ray_node_path, self.player.ray_queue)
        #播放模型动画
        self.player.loop("idle")
        def control_role(task):
            # Panda全局变量“ globalClock”可以访问自上次更新任务的时间,Vec3
            dt = globalClock.get_dt()
            self.player.update_role(self.key_map, dt)
            return task.cont
        # 使用任务管理器运行一个更新循环任务，调用一个名为“update_role”的方法。
        self.update_player = self.task_mgr.add(control_role, "update_role",)

        # 让相机跟随人物坐标变化
        def control_role_camera(task):
            self.camera.setPos(self.player.get_x(), -10 + self.player.get_y(), 10)
            return task.cont
        self.update_camera_pos = self.task_mgr.add(control_role_camera, "update_camera_pos",)

        # AI敌人
        self.enemy1 = Enemy(base=base, render=self.render, role_pos=(2, 2, 0), role_name='enemy1')
        self.pusher.add_collider(self.enemy1.collider, self.enemy1)
        self.cTrav.add_collider(self.enemy1.collider, self.pusher)
        #self.cTrav.add_collider(self.enemy1.attack_segment_node_path, self.pusher)
        self.enemy1.loop("walk")
        #self.enemy1.loop("attack")
        def ai_action_for_enemy(task):
            # Panda全局变量“ globalClock”可以访问自上次更新任务的时间,Vec3
            dt = globalClock.get_dt()
            self.enemy1.run_logic(self.player, dt)
            return task.cont
        self.update_enemy1 = self.task_mgr.add(ai_action_for_enemy, "update_enemy1",)

        self.trap_enemy1 = TrapEnemy(base=base, render=self.render, role_pos=(3, -2, 0), role_name='trap_enemy1')
        self.pusher.add_collider(self.trap_enemy1.collider, self.trap_enemy1)
        self.cTrav.add_collider(self.trap_enemy1.collider, self.pusher)

        # dt = globalClock.get_dt()
        # self.trap_enemy1.update(self.player, dt)
        #self.trap_enemy1.loop("walk")

        self.pusher.add_in_pattern("%fn-into-%in")

        self.accept("trapEnemy-into-wall", self.stop_trap)
        self.accept("trapEnemy-into-trapEnemy", self.stop_trap)
        self.accept("trapEnemy-into-player", self.trap_hits_something)
        self.accept("trapEnemy-into-walkingEnemy", self.trap_hits_something)

        self.comm_with_server = CommWithServer(role=self.player)
        # 登录服务器
        login_thread = threading.Thread(target=self.comm_with_server.login_server, args=("abcd1", "123"), name="登录")
        login_thread.setDaemon(True)
        login_thread.start()
        #self.comm_with_server.login_server(user_name="abcd1", passwd="123")

        # 使用一个简单的字典，将键名映射到键状态。“ True”表示按键被按下；“ False”表示不是。
        self.key_map = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "jump": False,
            "run": False,
            "shoot": False
        }

        # 事件由“ DirectObject”类的对象处理。ShowBase是DirectObject的子类，而我们的游戏是ShowBase的子类。游戏类可以处理事件。
        # 告诉DirectObject让它接收事件,w、w-up代表键盘W按下和弹起
        self.accept("e", self.update_key_map, ["up", True])
        self.accept("e-up", self.update_key_map, ["up", False])
        self.accept("d", self.update_key_map, ["down", True])
        self.accept("d-up", self.update_key_map, ["down", False])
        self.accept("s", self.update_key_map, ["left", True])
        self.accept("s-up", self.update_key_map, ["left", False])
        self.accept("f", self.update_key_map, ["right", True])
        self.accept("f-up", self.update_key_map, ["right", False])
        self.accept("space", self.update_key_map, ["jump", True])
        self.accept("a", self.update_key_map, ["run", True])
        self.accept("a-up", self.update_key_map, ["run", False])
        self.accept("mouse1", self.update_key_map, ["shoot", True])
        self.accept("mouse1-up", self.update_key_map, ["shoot", False])


    def stop_trap(self, entry):
        client_logger.debug("执行Game.stop_trap()")
        collider = entry.get_from_node_path()
        if collider.has_python_tag("owner"):
            trap = collider.getPythonTag("owner")
            trap.moveDirection = 0
            trap.ignorePlayer = False

    def trap_hits_something(self, entry):
        client_logger.debug("执行Game.trap_hits_something()")
        collider = entry.getFromNodePath()
        if collider.hasPythonTag("owner"):
            trap = collider.getPythonTag("owner")

            # We don't want stationary traps to do damage,
            # so ignore the collision if the "moveDirection" is 0
            if trap.moveDirection == 0:
                return

            collider = entry.getIntoNodePath()
            if collider.has_python_tag("owner"):
                obj = collider.get_python_tag("owner")
                if isinstance(obj, Player):
                    if not trap.ignorePlayer:
                        obj.alterHealth(-1)
                        trap.ignorePlayer = True
                else:
                    obj.alterHealth(-10)


    def get_update_palyer_data(self):
        data = {
        "request_type": "update_player",
        "role_id": self.player.role_id,
        "role_name": self.player.role_name,
        "time": time.time(),
        "pos": list(self.player.get_pos()),
        "setH": self.player.get_h(),
        "action": None,
        }
        return data


    def update_key_map(self, control_name, control_state):
        self.key_map[control_name] = control_state
        data = self.get_update_palyer_data()
        self.comm_with_server.send_server_tcp(data)
        #client_logger.info("%s键, 设置为了 %s" % (control_name, control_state))


if __name__ == "__main__":
    app = Game()
    app.run()