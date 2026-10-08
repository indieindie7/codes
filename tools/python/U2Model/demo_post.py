"""U2Model demo: a small guard post combined from basic shapes (adds and subtracts)."""
from u2model import box, stairs, cylinder, dome, arch, tube, wedge


def model():
    post = box(512, 512, 320).move(0, 0, 64)                         # the block, on a 64 plinth
    post += box(640, 640, 64)                                        # plinth
    post -= box(448, 448, 280).move(0, 0, 84)                        # hollow it
    post -= box(128, 80, 224).move(0, -236, 84)                      # the door (front, -y)
    post -= box(192, 80, 64).move(0, 236, 240)                       # a window slot at the back
    post += stairs(160, 4, rise=16, run=40).rotate(yaw=90).move(0, -480, 0)   # steps up to the plinth, from the front
    post += cylinder(40, 448, 12).move(300, -300, 0)                 # a corner pillar
    post += dome(56, 12, 4).move(300, -300, 448)                     # its lamp cap
    post += arch(384, 320, 48, 160, 160).move(0, -720, 0)            # a gate arch in front
    post += tube(48, 36, 384, 12).move(-300, 300, 0)                 # a vent pipe
    post += wedge(256, 128, 64).rotate(yaw=180).move(-448, 0, 0)    # a ramp up the side
    return post


if __name__ == "__main__":
    m = model()
    print("problems:", m.check() or "none")
    print(len(m.steps), "steps;", m.preview("demo_post.png", title="guard post (mock-up: red = cut away)"))
