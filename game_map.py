from panda3d.core import CollisionNode, CollisionTube, CollisionBox, AmbientLight, Vec4, DirectionalLight
from FreedomCampaignGame.comm_with_server import ClientLogObject
client_logger = ClientLogObject().client_logger

class GameMap():
    def __init__(self, render, load_model_fun):
        self.render = render
        # 加载环境模型。将加载models文件夹中的environment.egg文件，返回该模型的指针
        self.load_model = load_model_fun
        self.scene = self.load_model("Models/Environment/environment")
        # 重新绘制要 渲染的模型。
        self.scene.reparent_to(self.render)
        client_logger.info("开始生成地图障碍物...")
        self.set_map_solid()
        client_logger.info("加载环境光、定向灯光..")
        self.load_light_all()

    def load_light_all(self):
        # 添加环境光, AmbientLight对象是一个节点
        self.ambient_light = AmbientLight("ambient light")
        self.ambient_light.set_color(Vec4(0.2, 0.2, 0.2, 1))
        self.ambient_light_node_path = self.render.attach_new_node(self.ambient_light)
        # 环境灯光默认自动影响指示节点下方的所有节点，希望灯光影响所有节点场景，则需要在render(渲染)上指定灯光
        self.render.set_light(self.ambient_light_node_path)
        # 添加定向光，可指定方向
        self.directional_light = DirectionalLight("directional light")
        self.directional_light_node_path = self.render.attach_new_node(self.directional_light)
        # 一个正面对着你的人，H相当于它左转，P相当于它向左倒也就是顺时针转，R是往前向你这边扑倒旋转，光照射出的位置变动
        self.directional_light_node_path.setHpr(45, -45, 0)
        self.render.set_light(self.directional_light_node_path)
        # 应用着色器生成器，希望它影响的NodePath上调用“ setShaderAuto”即可。这里是将着色器生成器应用于“渲染”
        self.render.setShaderAuto()

    def set_box_solid(self, size=(0, 1, 1, 1), show=True):
        # size, 第一个0暂时不知道干嘛，官网文档也没说明，后面3分别是长宽高
        box_solid = CollisionBox(size[0], size[1], size[2], size[3])
        box_node = CollisionNode("box")
        box_node.add_solid(box_solid)
        box = self.render.attach_new_node(box_node)
        if show:
            box.show()
        return box

    def set_tube_solid(self, size=(0, 0, 0, 0, 0, 0, 0.4), show=True):
        # 管由其起点、终点和半径定义。这里定义的一个管子物体从（-8，0，0）到为（8，0，0），半径为0.4的圆形管道
        set_tube_solid = CollisionTube(size[0], size[1], size[2], size[3], size[4], size[5], size[6])
        wall_node = CollisionNode("wall")
        wall_node.add_solid(set_tube_solid)
        wall = self.render.attach_new_node(wall_node)
        if show:
            wall.show()
        return wall

    def set_map_solid(self):
        # 放一个大的管子
        # wall = self.set_tube_solid(size=(-2.0, 0, 0, 2.0, 0, 0, 0.2))
        # wall.setY(-3)
        # 用box设置楼梯
        box = self.set_box_solid(size=(0, 1, 1.5, 0.2))
        box.setX(-2)
        box.setZ(0.2)
        box = self.set_box_solid(size=(0, 1, 1.5, 0.4))
        box.setX(-3)
        box.setZ(0.4)
        box = self.set_box_solid(size=(0, 1, 1.5, 0.6))
        box.setX(-4)
        box.setZ(0.6)

        # 用box设置墙，这里是弄门这里的两面墙
        box = self.set_box_solid(size=(0, 3.65, 0.1, 1.5))
        box.setY(8.1)
        box.setX(-4.3)
        box.setZ(1.5)
        box = self.set_box_solid(size=(0, 3.65, 0.1, 1.5))
        box.setY(8.1)
        box.setX(4.3)
        box.setZ(1.5)
        # 弄门，门栏
        box = self.set_box_solid(size=(0, 0.65, 0.1, 0.25))
        box.setY(8.2)
        box.setZ(0.25)
        # 门顶部
        box = self.set_box_solid(size=(0, 0.65, 0.1, 0.2))
        box.setY(8.1)
        box.setZ(2.04)

        box = self.set_box_solid(size=(0, 8, 0.1, 1.5))
        box.setY(-8.1)
        box.setZ(1.5)
        box = self.set_box_solid(size=(0, 0.1, 8, 1.5))
        box.setX(8.1)
        box.setZ(1.5)
        box = self.set_box_solid(size=(0, 0.1, 8, 1.5))
        box.setX(-8.1)
        box.setZ(1.5)