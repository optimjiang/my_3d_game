from FreedomCampaignGame.comm_with_server import ClientLogObject
from direct.actor.Actor import Actor
from panda3d.core import CollisionNode, CollisionCapsule, CollisionBox, Vec2, Vec3, CollisionRay, \
    CollisionHandlerQueue, BitMask32, Plane, Point3, CollisionSegment, TextNode, Vec4, PointLight
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage

import math
import sys
import random
import time

client_logger = ClientLogObject().client_logger
# 摩擦力
FRICTION = 150.0


class Role(Actor):
    def __init__(self, base, render, role_model, model_animations, role_collider, collider_name, role_id, role_name,
                 role_pos,
                 max_health, health, max_speed, speed, max_jump_height, jump_height):
        client_logger.debug("执行Role.__init__()")
        Actor.__init__(self, models=role_model, anims=model_animations)
        # self = Actor(models=role_model, anims=model_animations)
        self.base = base
        self.render = render
        # 加载角色模型，和角色动画名称和定义这些动画的动画文件，注意不要被环境模型挡住,不然可能看不到
        self.reparent_to(self.render)
        self.role_id = role_id
        self.role_name = role_name
        self.set_pos(role_pos)
        # 重力，用来控制下降、跳跃的速度
        self.gravity = 3.0
        # 最大健康值
        self.max_health = max_health
        self.health = health
        self.max_speed = max_speed
        self.max_jump_height = max_jump_height
        self.speed = speed
        self.jump_height = jump_height
        self.starting_height = 0
        self.history_hight_list = []

        self.walking = False
        self.attacking = False
        self.dying = False

        # 获得碰撞节点，参数是碰撞节点的名称
        collider_node = CollisionNode(collider_name)
        collider_node.add_solid(role_collider)
        self.collider = self.attach_new_node(collider_node)
        # 显示出碰撞体，用于测试和调试
        # self.collider.show()

        # 在对撞机中存储对Role的引用，当发生碰撞时，我们可以访问所涉及的对撞机，
        # Role正在存储对撞机的引用，并且通过添加指向Role的Python标签，对撞机现在具有对GameObject的引用。
        self.collider.set_python_tag("owner", self)

        # 旋转角色模型的子节点，不要旋转模型，不然后面的旋转会变得逻辑复杂，"H"、"P"、"R"分别是不同航向的旋转
        # 一个正面对着你的人，H相当于它左转，P相当于它向左倒也就是顺时针转，R是往前向你这边扑倒旋转，
        # self.getChild(0).setR(0)

        # 沿着一个方向的速度，x,y,z 3个方向的速度
        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 300.0

    def update(self, dt):
        # client_logger.debug("执行Role.update()")
        # 如果我们的速度超过我们的最高速度，这里的速度speed貌似是指当前速度移动的距离值
        # 将速度向量的长度设置为该最大值
        speed = self.velocity.length()
        if speed > self.max_speed:
            self.velocity.normalize()
            self.velocity *= self.max_speed
            speed = self.max_speed

        # 如果我们没有走路，不用担心摩擦力。否则，用摩擦力来减缓我们的速度。
        if not self.walking:
            # 计算设定的摩擦倍数阻碍的移动值
            frictionVal = FRICTION * dt
            if frictionVal > speed:
                self.velocity.set(0, 0, 0)
            else:
                # 摩擦值小于速度的话，摩擦矢量=负的 沿着一个方向的速度值？再乘以摩擦阻碍的移动值
                frictionVec = -self.velocity
                frictionVec.normalize()
                # 乘以frictionVal = FRICTION*dt，就能按设定的摩擦倍数得到最终应该的摩擦力阻碍的移动值
                frictionVec *= frictionVal
                self.velocity += frictionVec

        # Move the character, using our velocity and
        # the time since the last update.
        self.set_pos(self.get_pos() + self.velocity * dt)

    def alter_health(self, d_health):
        client_logger.debug("执行Role.alter_health()")
        # 改变健康值
        self.health += d_health
        if self.health > self.max_health:
            self.health = self.max_health
        elif self.health < 0:
            self.health = 0
        client_logger.debug("%s当前健康值: %s" % (type(self).__name__, self.health))
        if self.health <= 0:
            try:
                self.loop("die")
                client_logger.debug("%s已死亡" % type(self).__name__)
            except:
                pass

    def cleanup(self):
        client_logger.debug("执行Role.cleanup()")
        # 删除各种节点，并清除Python标记
        if self.collider is not None and not self.collider.is_empty():
            self.collider.clear_python_tag("owner")
            self.base.cTrav.remove_collider(self.collider)
            self.base.pusher.remove_collider(self.collider)
        if self is not None:
            self.cleanup()
            self.remove_node()
            self = None
        self.collider = None


class Player(Role):
    def __init__(self, base, load_model_fun, render, role_model="Models/Role_Chan/act_p3d_chan",
                 model_animations={"walk": "Models/Role_Chan/a_p3d_chan_walk",
                                   "idle": "Models/Role_Chan/a_p3d_chan_idle",
                                   "run": "Models/Role_Chan/a_p3d_chan_run",
                                   "step_l": "Models/Role_Chan/a_p3d_chan_step_l",
                                   "step_r": "Models/Role_Chan/a_p3d_chan_step_r"},
                 role_collider=CollisionCapsule(0, 0, 0, 0, 0, 1.1, 0.2),
                 collider_name='player',
                 role_id=None, role_name='plaer1', role_pos=(0, 0, 0), max_health=10, health=10,
                 max_speed=3, speed=0, max_jump_height=0.8, jump_height=0.75):
        client_logger.debug("执行Player.__init__()")
        Role.__init__(self, base, render, role_model, model_animations, role_collider, collider_name,
                      role_id, role_name, role_pos, max_health, health,
                      max_speed, speed, max_jump_height, jump_height)

        self.load_model_fun = load_model_fun
        self.run_speed = 2.4
        self.walk_speed = 0.8
        self.idling = True
        self.running = False
        self.jumping = False
        self.jump_downing = False
        self.jump_down = False
        self.falling = False

        # 在模型上应用缩放，调整位置
        self.set_scale(0.8, 0.8, 0.8)
        self.collider.setZ(0.2)
        self.getChild(0).setH(180)

        # 弄一个射线类的碰撞体作为攻击技能加到角色节点中
        self.ray = CollisionRay(0, 0, 0, 0, 0.8, 0)
        ray_node = CollisionNode("player_ray")
        ray_node.add_solid(self.ray)
        self.ray_node_path = self.attach_new_node(ray_node)
        self.ray_queue = CollisionHandlerQueue()
        # 添加射线类的碰撞节点
        base.cTrav.add_collider(self.ray_node_path, self.ray_queue)
        self.ray_node_path.setZ(0.7)
        self.ray_node_path.show()
        self.damage_per_second = -5.0
        # 碰撞系统设置碰撞对象可以碰撞到的东西，比如用来设置碰撞对象可以攻击的对象, 这样不会和人碰撞？
        mask = BitMask32()
        mask.setBit(1)
        # 大概意思是将它设置为可以碰撞到from设置为1号mask的碰撞体
        self.collider.node().set_into_collide_mask(mask)
        mask = BitMask32()
        mask.setBit(1)
        # 大概意思是将它设置为可以被into设置为1号mask碰撞到
        self.collider.node().set_from_collide_mask(mask)

        # 我们在这里设置了一个不同的点！这意味着光线攻击的遮罩和碰撞体的遮罩不匹配，因此光线不会与光线的碰撞体碰撞。
        mask = BitMask32()
        mask.setBit(2)
        # 大概意思是光线攻击可以被2号mask碰撞到
        ray_node.set_from_collide_mask(mask)
        mask = BitMask32()
        # 大概意思是光线攻击可以碰撞到from设置为0号mask的碰撞体
        ray_node.set_into_collide_mask(mask)

        # 激光模型
        self.beam_model = self.load_model_fun("Models/BambooLaser/bambooLaser")
        self.beam_model.reparent_to(self)
        self.beam_model.setZ(0.7)
        self.beam_model.setLightOff()
        self.beam_model.hide()

        # 攻击闪光效果
        self.beam_hit_model = self.load_model_fun("Models/BambooLaser/bambooLaserHit")
        self.beam_hit_model.reparent_to(self)
        self.beam_hit_model.setZ(1.5)
        self.beam_hit_model.setLightOff()
        self.beam_hit_model.hide()
        self.beam_hit_pulse_rate = 0.15
        self.beam_hit_timer = 0
        self.beam_hit_light = PointLight("beam_hit_light")
        self.beam_hit_light.set_color(Vec4(0.1, 1.0, 0.2, 1))
        self.beam_hit_light.set_attenuation((1.0, 0.1, 0.5))
        self.beam_hit_light_node_path = self.render.attach_new_node(self.beam_hit_light)

        # 被攻击时的红色闪光效果
        self.damage_taken_model = self.load_model_fun("Models/BambooLaser/playerHit")
        self.damage_taken_model.reparent_to(self)
        self.damage_taken_model.setH(0.7)
        self.damage_taken_model.setZ(1.0)
        self.damage_taken_model.set_light_off()
        self.damage_taken_model.hide()
        self.damage_taken_model_timer = 0
        self.damage_taken_model_duration = 0.15

        # 鼠标默认坐标
        self.last_mouse_pos = Vec2(0, 0)
        self.ground_plane = Plane(Vec3(0, 0, 1), Vec3(0, 0, 0))
        self.yVector = Vec2(0, 1)

        # 弄分数
        self.score = 0
        self.score_ui = OnscreenText(text="0",
                                     pos=(-1.3, 0.725),
                                     mayChange=True,
                                     align=TextNode.A_left)
        # 弄血条
        self.health_icons = []
        for i in range(math.ceil(self.max_health / 1)):
            icon = OnscreenImage(image="UI/health.png",
                                 pos=(-1.175 + i * 0.075, 0, 0.85),
                                 scale=0.03)
            icon.set_transparency(True)
            self.health_icons.append(icon)

    def update_role(self, key_map, dt):
        # 被攻击时的动画更新
        if self.damage_taken_model_timer > 0:
            self.damage_taken_model_timer -= dt
            self.damage_taken_model.setScale(2.0 - self.damage_taken_model_timer / self.damage_taken_model_duration)
        if self.damage_taken_model_timer <= 0:
            self.damage_taken_model.hide()

        # client_logger.debug("执行Player.update_role()")
        # 处理鼠标相关,这里计算的坐标似乎不太符合3d场景，需要重新自己计算
        # 当没有鼠标(比如在窗口外面)，则使用前面的位置
        mouse_watcher = self.base.mouseWatcherNode
        if mouse_watcher.hasMouse():
            mouse_pos = mouse_watcher.getMouse()
        else:
            mouse_pos = self.last_mouse_pos
        mouse_pos_3d = Point3()
        near_point = Point3()
        far_point = Point3()
        self.base.camLens.extrude(mouse_pos, near_point, far_point)
        self.ground_plane.intersectsLine(mouse_pos_3d,
                                         self.render.getRelativePoint(self.base.camera, near_point),
                                         self.render.getRelativePoint(self.base.camera, far_point))
        firing_vector = Vec3(mouse_pos_3d - self.get_pos())
        firingVector2D = firing_vector.getXy()
        firingVector2D.normalize()
        firing_vector.normalize()
        heading = self.yVector.signed_angle_deg(firingVector2D)
        self.setH(heading)
        self.last_mouse_pos = mouse_pos

        self.walking = False
        if key_map['run']:
            # client_logger.debug(key_map)
            self.speed = self.run_speed
            self.running = True
        else:
            self.speed = self.walk_speed
            self.running = False
        # client_logger.debug(key_map)
        # 跳跃的优先级应该最高
        if key_map["jump"] and not self.jump_downing and not self.falling:
            self.jump(key_map, dt)
        # 当站在较高的地方走动的时候，得判断是否能掉下去，和跳跃设定为冲突关系，避免多个方向键+跳跃会出现瞬移
        elif self.jump_downing:
            self.gravitation(dt)
            self.jump_down = False
        if key_map["up"]:
            self.walking = True
            pos = self.get_pos()
            setpos = pos + Vec3(0, self.speed * dt, 0)
            self.set_pos(setpos)
            self.getChild(0).setH(180)
            if not self.jump_downing and self.jump_height > 0:
                self.jump_down = True
        if key_map["down"]:
            self.walking = True
            pos = self.get_pos()
            setpos = pos + Vec3(0, -self.speed * dt, 0)
            self.set_pos(setpos)
            self.getChild(0).setH(0)
            if not self.jump_downing and self.jump_height > 0:
                self.jump_down = True
        if key_map["left"]:
            self.walking = True
            pos = self.get_pos()
            setpos = pos + Vec3(-self.speed * dt, 0, 0)
            self.set_pos(setpos)
            self.getChild(0).setH(-90)
            if not self.jump_downing and self.jump_height > 0:
                self.jump_down = True
        if key_map["right"]:
            self.walking = True
            pos = self.get_pos()
            setpos = pos + Vec3(self.speed * dt, 0, 0)
            self.set_pos(setpos)
            self.getChild(0).setH(90)
            if not self.jump_downing and self.jump_height > 0:
                self.jump_down = True
        # 移动后激活一下下落的逻辑
        if self.jump_down and not self.jumping and self.jump_height > 0:
            # client_logger.debug("移动触发下落")
            self.gravitation(dt)
        if key_map["shoot"]:
            self.ray_attack(firing_vector, dt)
        else:
            self.beam_model.hide()
        self.update_anim()

    def update_anim(self):
        # 根据不同情况播放不同动画
        if self.jumping:
            if self.get_anim_control("idle").is_playing():
                self.stop("idle")
            if self.get_anim_control("walk").is_playing():
                self.stop("walk")
            if self.get_anim_control("run").is_playing():
                self.stop("run")
            if not self.get_anim_control("step_l").is_playing():
                self.loop("step_l")
        elif self.jump_downing or self.falling:
            if self.get_anim_control("idle").is_playing():
                self.stop("idle")
            if self.get_anim_control("step_l").is_playing():
                self.stop("step_l")
            if self.get_anim_control("walk").is_playing():
                self.stop("walk")
            if self.get_anim_control("run").is_playing():
                self.stop("run")
            if not self.get_anim_control("step_r").is_playing():
                self.loop("step_r")
        elif self.running and self.walking:
            if self.get_anim_control("walk").is_playing():
                self.stop("walk")
            if not self.get_anim_control("run").is_playing():
                self.loop("run")
        elif self.walking:
            if self.get_anim_control("run").is_playing():
                self.stop("run")
            if not self.get_anim_control("walk").is_playing():
                self.loop("walk")
        else:
            if self.get_anim_control("run").is_playing():
                self.stop("run")
            if self.get_anim_control("walk").is_playing():
                self.stop("walk")
            if self.get_anim_control("step_l").is_playing():
                self.stop("step_l")
            if not self.get_anim_control("idle").is_playing():
                self.loop("idle")

    def jump(self, key_map, dt):
        pos = self.get_pos()
        # client_logger.debug("跳跃，实时坐标 %s" % pos)
        if not self.jumping:
            self.starting_height = pos[2]
            self.jumping = True
            self.current_height = self.starting_height
        setpos = pos + Vec3(0, 0, self.gravity * dt)
        self.set_pos(setpos)
        # 跳跃过程中实时高度
        self.current_height = self.current_height + self.gravity * dt
        if self.current_height >= self.jump_height + self.starting_height:
            setpos = (pos[0], pos[1], self.jump_height + self.starting_height)
            self.set_pos(setpos)
            key_map["jump"] = False
            self.jumping = False
            self.jump_downing = True
            # self.jump_height = max_height
            self.history_hight_list = []

    def gravitation(self, dt):
        # 因引力而下降
        pos = self.get_pos()
        height = pos[2]
        self.history_hight_list.append(height)
        if height <= 0:
            setpos = (pos[0], pos[1], 0)
            self.set_pos(setpos)
            self.jump_downing = False
            self.jump_down = False
            # client_logger.debug("height:%s" % height)
            self.history_hight_list = []
            self.falling = False
            return
        elif len(self.history_hight_list) > 2:
            hhl = self.history_hight_list
            if hhl[-2] - hhl[-1] < 0.01:
                # client_logger.debug("history_hight:%s" % self.history_hight_list)
                self.jump_downing = False
                self.jump_down = False
                self.falling = False
                self.history_hight_list = [height]
                return
            else:
                self.falling = True
        setpos = pos + Vec3(0, 0, -self.gravity * dt)
        self.set_pos(setpos)

    def ray_attack(self, firing_vector, dt):
        client_logger.debug("执行Player.ray_attack()")
        # 拿到光线碰到的目标数
        if self.ray_queue.get_num_entries() > 0:
            scored_hit = False
            self.ray_queue.sort_entries()
            # 拿到第一个碰到的目标
            ray_hit = self.ray_queue.get_entry(0)
            hit_pos = ray_hit.get_surface_point(self.render)
            hit_node_path = ray_hit.get_into_node_path()
            if hit_node_path.has_python_tag("owner"):
                hit_object = hit_node_path.get_python_tag("owner")
                client_logger.debug("%s用射线攻击到的对象是 : %s" % (type(self).__name__, type(hit_object).__name__))
                if isinstance(hit_object, Enemy):
                    hit_object.alter_health(self.damage_per_second * dt)
                    scored_hit = True
            beam_length = (hit_pos - self.get_pos()).length()
            if firing_vector.length() > 0.001:
                self.ray.set_origin(self.get_pos())
                self.ray.set_direction(firing_vector)
                # self.ray.set_origin(self.get_pos())
                # self.ray.set_direction(firing_vector)
                self.beam_model.setSy(beam_length)
            # 击中后的攻击动画效果
            if scored_hit:
                self.beam_hit_model.show()
                self.beam_hit_model.set_pos(hit_pos)
                self.beam_hit_light_node_path.set_pos(hit_pos + Vec3(0, 0, 0.5))
                if not self.render.has_light(self.beam_hit_light_node_path):
                    self.render.set_light(self.beam_hit_light_node_path)
            else:
                if self.render.has_light(self.beam_hit_light_node_path):
                    self.render.clear_light(self.beam_hit_light_node_path)
                self.beam_hit_model.hide()
        else:
            self.beam_model.setSy(100)
            if self.render.has_light(self.beam_hit_light_node_path):
                # 把击中的闪光效果从现场清除，这样不再照亮任何东西
                self.render.clear_light(self.beam_hit_light_node_path)
            self.beam_model.hide()
            self.beam_hit_model.hide()
        self.beam_model.show()

    def update_score(self):
        self.score_ui.set_text(str(self.score))

    def alter_health(self, d_health):
        self.damage_taken_model.show()
        self.damage_taken_model.setH(random.uniform(0.0, 360.0))
        self.damage_taken_model_timer = self.damage_taken_model_duration
        Role.alter_health(self, d_health)
        for index, icon in enumerate(self.health_icons):
            if index < math.ceil(self.health / 1):
                icon.show()
            else:
                icon.hide()

    def cleanup(self):
        client_logger.debug("执行Player.cleanup()")
        self.beam_model.remove_node()
        self.render.clear_light(self.beam_hit_light_node_path)
        self.beam_hit_light_node_path.remove_node()
        self.score_ui.remove_node()
        for icon in self.health_icons:
            icon.remove_node()
        self.base.cTrav.remove_collider(self.ray_node_path)
        # Role.cleanup(self)


class Enemy(Role):
    # 两轮子角色
    def __init__(self, base, render, role_model="Models/SimpleEnemy/simpleEnemy",
                 model_animations={
                     "spawn": "Models/SimpleEnemy/simpleEnemy-spawn",
                     "stand": "Models/SimpleEnemy/simpleEnemy-stand",
                     "walk": "Models/SimpleEnemy/simpleEnemy-walk",
                     "attack": "Models/SimpleEnemy/simpleEnemy-attack",
                     "die": "Models/SimpleEnemy/simpleEnemy-die"},
                 role_collider=CollisionCapsule(0, 0, 0, 0, 0, 1.23, 0.3),
                 collider_name='enemy',
                 role_id=None, role_name='enemy1', role_pos=(0, 0, 0), max_health=50, health=50,
                 max_speed=2, speed=0.5, max_jump_height=0, jump_height=0):
        client_logger.debug("执行Enemy.__init__()")
        Role.__init__(self, base, render, role_model, model_animations, role_collider, collider_name,
                      role_id, role_name, role_pos, max_health, health,
                      max_speed, speed, max_jump_height, jump_height)

        self.set_scale(0.8, 0.8, 0.8)
        self.collider.setZ(0.28)

        self.spawning = True
        self.spawning_timer = 1.0
        # self.loop("spawn")
        self.standing = True

        # 攻击力
        self.attack_damage = -1
        # 攻击距离
        self.attack_distance = 0.8
        # 攻击间隔
        self.attack_wait_timer = 1.0
        # 攻击定时器
        self.attack_delay_timer = self.attack_wait_timer
        self.attack_remaining_animation_timer = 0.5
        self.attack_anim_delay_timer = self.attack_remaining_animation_timer
        self.attack_remaining_animation = False
        # 加速度
        self.acceleration = 100.0

        # 用于确定怎么面对要攻击的人方向，因为角色面朝y方向，我们用y轴。
        self.yVector = Vec2(0, 1)

        # 弄一个射线节点
        self.attack_segment = CollisionSegment(0, 0, 0, 0, 0.6, 0)
        segment_node = CollisionNode("enemy_attack_segment")
        segment_node.add_solid(self.attack_segment)
        mask = BitMask32()
        mask.setBit(1)
        # 将它设置为 可以接受来自设置为1号mask的碰撞体碰撞
        segment_node.set_from_collide_mask(mask)
        mask = BitMask32()
        # 将它设置为 可以碰撞到设置为0号mask的碰撞体
        segment_node.set_into_collide_mask(mask)

        # 添加一个新的碰撞体(射线)节点
        self.attack_segment_node_path = self.render.attach_new_node(segment_node)
        self.attack_segment_node_path.setZ(1)
        self.segment_queue = CollisionHandlerQueue()
        # 添加射线的碰撞节点到碰撞体系中
        base.cTrav.add_collider(self.attack_segment_node_path, self.segment_queue)
        self.attack_segment_node_path.show()

        # 碰撞系统设置碰撞对象可以碰撞到的东西，比如用来设置碰撞对象可以攻击的对象, 这样不会和人碰撞？
        mask = BitMask32()
        mask.setBit(2)
        # 人物的光线也设置为了2，这样就可以攻击这个两轮机器人了
        self.collider.node().set_into_collide_mask(mask)

    def run_logic(self, player, dt):
        if self.spawning:
            self.spawning_timer -= dt
            if self.spawning_timer < 0:
                self.spawning = False
            return
        if player.health < 0:
            return
        # client_logger.debug("执行Enemy.run_logic()")
        # 设置线段的起点和终点。
        self.attack_segment.set_point_a(self.get_pos())
        # “getQuat”返回一个四元数——表示方向或旋转——代表NodePath的方向。这在这里很有用，
        # 因为Panda的四元数类有方法该方向的前、右和上方向向量。因此，我们要做的是使段指向“前进”。
        self.attack_segment.set_point_b(self.get_pos() + self.get_quat().get_forward() * self.attack_distance)

        # 找出敌人和玩家。如果敌人离玩家很远，使用该向量enemy 向玩家移动。否则，就暂时停下来。最后，方向改成面朝玩家
        vector_to_player = player.get_pos() - self.get_pos()
        vector_to_player2D = vector_to_player.getXy()
        distance_to_player = vector_to_player2D.length()
        # 规范化一下数据
        vector_to_player2D.normalize()

        # 通过与玩家的X、Y轴差，来算出俯视角度
        heading = self.yVector.signed_angle_deg(vector_to_player2D)
        # 与玩家的距离 > 攻击距离*0.9就移动
        if distance_to_player > self.attack_distance * 0.9 and not self.attacking:
            self.walking = True
            self.update(dt)
            # 它不能跳跃，让它一直只能呆在地面
            vector_to_player.setZ(0)
            vector_to_player.normalize()
            self.velocity += vector_to_player * self.acceleration * dt
        # self.attack_wait_timer = 0.2
        # self.attack_delay_timer = 0
        else:
            self.walking = False
            self.attacking = True
            self.velocity.set(0, 0, 0)
            # 等待攻击
            if self.attack_delay_timer - self.attack_remaining_animation_timer > 0:
                self.attack_delay_timer -= dt
            else:
                # 攻击之后还有硬直和后续动作等，需要等待这些完后才能进行下次攻击
                if self.attack_remaining_animation:
                    self.attack_anim_delay_timer -= dt
                    # 攻击到目标时，还需
                    if self.attack_anim_delay_timer < 0:
                        self.attack_delay_timer = self.attack_wait_timer
                        self.attack_remaining_animation = False
                        self.attacking = False
                        self.attack_anim_delay_timer = self.attack_remaining_animation_timer
                else:
                    # 攻击的时间(动作)中就造成伤害，不然动作太滞后了
                    # 检查有没有击中目标
                    if self.segment_queue.get_num_entries() > 0:
                        self.segment_queue.sort_entries()
                        # 这里暂时只攻击一个目标
                        segment_hit = self.segment_queue.get_entry(0)
                        hit_node_path = segment_hit.get_into_node_path()
                        if hit_node_path.has_python_tag("owner"):
                            hit_object = hit_node_path.get_python_tag("owner")
                            client_logger.debug("%s攻击到的对象是: %s" % (type(self).__name__, type(hit_object).__name__))
                            hit_object.alter_health(self.attack_damage)
                    self.attack_remaining_animation = True

            # # 如果我们等着被允许攻击。。。
            # elif self.attack_wait_timer > 0:
            #     self.attack_wait_timer -= dt
            #     # 如果等待结束了就发起攻击
            #     if self.attack_wait_timer <= 0:
            #         # 发动攻击!并将等待计时器设置为随机值，把事情稍微改变一下。
            #         self.attack_wait_timer = random.uniform(0.5, 0.7)
            #         self.attack_delay_timer = self.attack_delay
            #         self.play("attack")
        self.setH(heading)
        self.update_anim()

    def update_anim(self):
        spawn_control = self.get_anim_control("spawn")
        walk_control = self.get_anim_control("walk")
        stand_control = self.get_anim_control("stand")
        attack_control = self.get_anim_control("attack")
        die_control = self.get_anim_control("die")

        if not self.spawning and spawn_control.is_playing():
            self.stop("spawn")
        if not self.walking and walk_control.is_playing():
            self.stop("walk")
        if not self.standing and stand_control.is_playing():
            self.stop("stand")
        if not self.attacking and attack_control.is_playing():
            self.stop("attack")
        if not self.dying and die_control.is_playing():
            self.stop("die")

        if spawn_control.is_playing():
            # 出生动画优先级第1
            return
        elif self.spawning:
            self.loop("spawn")
            return
        if die_control.is_playing():
            # 死亡动画优先级第2
            return
        elif self.dying:
            self.loop("die")
            return
        if attack_control.is_playing():
            # 攻击动画优先级第3
            return
        elif self.attacking:
            self.loop("attack")
            return
        if walk_control.is_playing():
            # 行走动画优先级第4
            return
        elif self.walking:
            self.loop("walk")
            return
        if stand_control.is_playing():
            self.loop("stand")

    def alter_health(self, damage):
        Role.alter_health(self, damage)
        # R、G、B、alpha
        self.set_color_scale(0, 0, 0, 1)
        if self.health <= 0:
            self.loop("die")
        self.clear_color_scale()
        # self.cleanup()

    def cleanup(self):
        client_logger.debug("执行Enemy.cleanup()")
        self.base.cTrav.remove_collider(self.attack_segment_node_path)
        self.attack_segment_node_path.remove_node()
        # Role.cleanup(self)


class TrapEnemy(Role):
    def __init__(self, base, render, role_model="Models/Trap/trap",
                 model_animations={
                     "stand": "Models/Trap/trap-stand",
                     "walk": "Models/Trap/trap-walk"},
                 role_collider=CollisionBox(0, 0.48, 0.48, 0.37),
                 collider_name='trap_enemy',
                 role_id=None, role_name='trap_enemy1', role_pos=(0, 0, 0), max_health=200, health=200,
                 max_speed=1, speed=1, max_jump_height=0, jump_height=0):
        client_logger.debug("执行Enemy.__init__()")
        Role.__init__(self, base, render, role_model, model_animations, role_collider, collider_name,
                      role_id, role_name, role_pos, max_health, health,
                      max_speed, speed, max_jump_height, jump_height)
        self.collider.setZ(0.38)
        # self.pusher.addCollider(self.collider, self)

        self.scoreValue = 1

        # 碰撞系统设置碰撞对象可以碰撞到的东西，比如用来设置碰撞对象可以攻击的对象, 这样不会和人碰撞？
        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)
        self.collider.node().set_into_collide_mask(mask)
        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)
        self.collider.node().set_from_collide_mask(mask)

    def update(self, player, dt):
        client_logger.debug("执行TrapEnemy.update()")
        Role.update(self, dt)
        self.run_logic(player, dt)
        if self.walking:
            walking_control = self.get_anim_control("walk")
            if not walking_control.is_playing():
                self.loop("walk")
        else:
            # 引发
            spawn_control = self.get_anim_control("spawn")
            if spawn_control is None or not spawn_control.is_playing():
                # 攻击动画
                attack_control = self.get_anim_control("attack")
                if attack_control is None or not attack_control.is_playing():
                    stand_control = self.get_anim_control("stand")
                    if not stand_control.is_playing():
                        self.loop("stand")

    def run_logic(self, player, dt):
        pass


class NPC(Role):
    def __init__(self):
        pass
