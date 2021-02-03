import abc


class Block:

    def __init__(self, duration, ax, start=None, clear_after_last=False, predcessor=None):
        self.start = start
        self.duration = duration
        self.ax = ax
        self.predcessor = predcessor
        self.last_artists = None
        self.clear_after_last = clear_after_last

    def is_last_frame(self, i):
        return i == self.duration - 1

    @abc.abstractmethod
    def provide_data(self, i, duration, frames_passed):
        pass

    @abc.abstractmethod
    def draw_figure(self, i, data, ax, last_artists, **kwargs):
        pass

    def update_figure(self, i, data, ax, last_artists):
        """
        Override this if you don't want to redraw plot and just update data instead
        """
        return self.draw_figure(i, data, ax, last_artists)

    def _plot(self, frames_passed):
        i = frames_passed - self.start
        data = self.provide_data(i, self.duration, frames_passed)

        if self.last_artists is None and self.predcessor is not None:
            self.last_artists = self.predcessor.last_artists

        has_previous_artists = self.last_artists is not None
        # print("has_previous_artists", has_previous_artists)

        if has_previous_artists:
            artists = self.update_figure(i, data, self.ax, self.last_artists)
        else:
            artists = self.draw_figure(i, data, self.ax, self.last_artists)

        self.last_artists = artists
        if self.is_last_frame(i) and self.clear_after_last:
            self.clear()
        return self.last_artists

    def is_time(self, frames_passed):
        # if duration==0 we have deal with timeless actions and need to handle them as well
        res = self.duration == 0 and frames_passed == self.start
        res |= self.start <= frames_passed < self.start + self.duration

        return res

    def clear(self):
        has_previous_artists = self.last_artists is not None
        if has_previous_artists:
            if self.last_artists in self.ax.lines:
                self.ax.lines.remove(self.last_artists)
            elif self.last_artists in self.ax.collections:
                self.ax.collections.remove(self.last_artists)


class AnimationHandler:
    """
    Class for creating actions and stacking them together to be handled sequentially when animation is running
    """

    def __init__(self, interval):
        self.frames = 0
        self.interval = interval
        self.blocks = []
        self.time_ticks = []
        self.dead_blocks_count = 0

    def add_block(self, block):
        if not block.start:
            block.start = self.frames
            self.frames += block.duration
        else:
            action_end = block.start + block.duration
            if action_end > self.frames:
                self.frames = action_end

        self.blocks.append(block)
        return block

    def update(self, frames_passed):
        artists = None
        for block_index, block in enumerate(self.blocks[self.dead_blocks_count:]):
            if block.is_time(frames_passed):
                if artists is None:
                    artists = []
                result = block._plot(frames_passed)
                if result:
                    artists.append(result)
        return artists

    def build_animation(self, fig):
        from matplotlib import animation
        ani = animation.FuncAnimation(
            fig=fig,
            func=self.update,
            frames=self.frames,
            interval=self.interval,
            blit=True)
        return ani


# HELPERS


class LineBlock(Block):

    @abc.abstractmethod
    def provide_data(self, i, duration, frames_passed):
        pass

    def draw_figure(self, i, data, ax, last_artists, **kwargs):
        x, y = data
        line, = ax.plot(x, y)
        return line

    def update_figure(self, i, data, ax, last_artists):
        if last_artists is None:
            return super().update_figure(data, ax, last_artists)
        x, y = data
        last_artists.set_data(x, y)
        return last_artists


class ScatterBlock(Block):

    @abc.abstractmethod
    def provide_data(self, i, duration, frames_passed):
        pass

    def draw_figure(self, i, data, ax, last_artists, **kwargs):
        x, y = data
        path = ax.scatter(x, y)
        return path

    def update_figure(self, i, data, ax, last_artists):
        if last_artists is None:
            return super().update_figure(data, ax, last_artists)
        path = last_artists
        x, y = data
        points = list(zip(x, y))
        path.set_offsets(points)

        return path


class FillBlock(Block):

    @abc.abstractmethod
    def provide_data(self, i, duration, frames_passed):
        pass

    def draw_figure(self, i, data, ax, last_artists, **kwargs):
        x, y1, y2 = data
        if 'from_update' in kwargs and kwargs.get('from_update'):
            poly_collection = ax.fill_between(x, y1, y2, color="grey", alpha=0.0)
        else:
            poly_collection = ax.fill_between(x, y1, y2)
        return poly_collection

    def update_figure(self, i, data, ax, last_artists):
        if last_artists is None:
            return super().update_figure(data, ax, last_artists)
        new_collection = self.draw_figure(i, data, ax, last_artists, from_update=True)
        # Here we want to change only the vertices and keep other parameters (like size or color) the same
        last_artists.get_paths()[0].vertices = new_collection.get_paths()[0].vertices
        ax.collections.remove(new_collection)
        return last_artists
