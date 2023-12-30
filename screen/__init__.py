class Screen:
    def update(self, display):
        raise NotImplementedError("called update() on generic Screen")

    def draw(self, overtaking, image_draw):
        raise NotImplementedError("called draw() on generic Screen")
