# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import os
from csv import DictWriter
from random import choice, shuffle

import klibs
from klibs import P
from klibs.KLCommunication import message
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import blit, fill, flip
from klibs.KLBoundary import CircleBoundary, BoundarySet
from klibs.KLTime import CountDown
from klibs.KLUserInterface import ui_request, key_pressed
from klibs.KLUtilities import pump

from natnetclient_rough import NatNetClient  # type: ignore[import]
from OptiTracker import OptiTracker  # type: ignore[import]

WHITE = (255, 255, 255, 255)
GRUE = (90, 90, 96, 255)
RED = (255, 0, 0, 255)

LEFT = "left"
RIGHT = "right"
SMALL = "small"
LARGE = "large"
TARGET = "target"
DISTRACTOR = "distractor"


class test_marker_pos_reporting(klibs.Experiment):

    def setup(self):

        # sizings
        PX_PER_CM = int(P.ppi / 2.54)
        DIAM_SMALL = 5 * PX_PER_CM
        DIAM_LARGE = 9 * PX_PER_CM
        BRIMWIDTH = 1 * PX_PER_CM
        POS_OFFSET = 10 * PX_PER_CM
        # setup optitracker
        self.ot = OptiTracker(marker_count=10, sample_rate=120, window_size=5)

        # setup motive client
        self.nnc = NatNetClient()

        # pass marker set listener to client for callback
        self.nnc.markers_listener = self.marker_set_listener

        self.locs = {
            LEFT: (P.screen_c[0] - POS_OFFSET, P.screen_c[1]),  # type: ignore[attr-defined]
            RIGHT: (P.screen_c[0] + POS_OFFSET, P.screen_c[1]),  # type: ignore[attr-defined]
        }

        self.sizes = {
            SMALL: DIAM_SMALL,
            LARGE: DIAM_LARGE,
        }

        # spawn object placeholders
        self.placeholders = {
            TARGET: {
                SMALL: kld.Annulus(DIAM_SMALL, BRIMWIDTH),
                LARGE: kld.Annulus(DIAM_LARGE, BRIMWIDTH),
            },
            DISTRACTOR: {
                SMALL: kld.Annulus(DIAM_SMALL, BRIMWIDTH),
                LARGE: kld.Annulus(DIAM_LARGE, BRIMWIDTH),
            },
        }

        self.cursor = kld.Annulus(
            diameter=PX_PER_CM, thickness=PX_PER_CM * 0.2, fill=RED
        )

        if not os.path.exists("OptiData"):
            os.mkdir("OptiData")

        os.mkdir(f"OptiData/{P.p_id}")

    def block(self):
        pass

    def trial_prep(self):
        self.ot.data_dir = f"OptiData/{P.p_id}/trial_{P.trial_number}.csv"  # type: ignore[attr-defined]

        locs = [LEFT, RIGHT]
        sizes = [SMALL, LARGE]

        shuffle(locs)

        self.target_loc, self.distractor_loc = locs
        self.target_size = choice(sizes)
        self.distractor_size = choice(sizes)

        self.target_boundary = CircleBoundary(
            label="target",
            center=self.locs[self.target_loc],  # type: ignore[attr-defined]
            radius=self.sizes[self.target_size],  # type: ignore[attr-defined]
        )

        self.distractor_boundary = CircleBoundary(
            label="distractor",
            center=self.locs[self.distractor_loc],  # type: ignore[attr-defined]
            radius=self.sizes[self.distractor_size],  # type: ignore[attr-defined]
        )

        self.bounds = BoundarySet([self.target_boundary, self.distractor_boundary])

        self.nnc.startup()
        lead_time = CountDown(0.05)

        while lead_time.counting():
            _ = ui_request()

    def trial(self):  # type: ignore[override]

        do_loop = True

        while do_loop:
            self.present_stimuli()

            q = pump(True)
            if key_pressed(key="space", queue=q):
                do_loop = False

        self.nnc.shutdown()

        return {"block_num": P.block_number, "trial_num": P.trial_number}

    def trial_clean_up(self):
        pass

    def clean_up(self):
        pass

    def present_stimuli(self):
        fill()

        distractor_holder = self.placeholders[DISTRACTOR][self.distractor_size]  # type: ignore[attr-defined]
        distractor_holder.fill = GRUE

        target_holder = self.placeholders[TARGET][self.target_size]  # type: ignore[attr-defined]
        target_holder.fill = WHITE

        cursor_pos = self.ot.position()

        xy_cursor = [cursor_pos["pos_x"][0].item(), cursor_pos["pos_z"][0].item()]
        message(
            text=f"X: {xy_cursor[0]:.2f}\nY: {xy_cursor[1]:.2f}",
            registration=2,
            location=(xy_cursor[0] - P.ppi, xy_cursor[1]),
            blit_txt=True,
        )

        xy_distractor = self.locs[self.distractor_loc]
        message(
            text=f"X: {xy_distractor[0]:.2f}\nY: {xy_distractor[1]:.2f}",
            registration=5,
            location=self.locs[self.distractor_loc],
            blit_txt=True,
        )

        xy_target = self.locs[self.target_loc]
        message(
            text=f"X: {xy_target[0]:.2f}\nY: {xy_target[1]:.2f}",
            registration=5,
            location=self.locs[self.target_loc],
            blit_txt=True,
        )

        blit(self.cursor, registration=5, location=xy_cursor)

        blit(
            distractor_holder,
            registration=5,
            location=self.locs[self.distractor_loc],
        )

        blit(target_holder, registration=5, location=self.locs[self.target_loc])

        flip()

    def marker_set_listener(self, marker_set: dict) -> None:
        """Write marker set data to CSV file.

        Args:
            marker_set (dict): Dictionary containing marker data to be written.
                Expected format: {'markers': [{'key1': val1, ...}, ...]}
        """

        if marker_set.get("label") == "hand":
            # Append data to trial-specific CSV file
            fname = self.ot.data_dir
            header = list(marker_set["markers"][0].keys())

            # if file doesn't exist, create it and write header
            if not os.path.exists(fname):
                with open(fname, "w", newline="") as file:
                    writer = DictWriter(file, fieldnames=header)
                    writer.writeheader()

            # append marker data to file
            with open(fname, "a", newline="") as file:
                writer = DictWriter(file, fieldnames=header)
                for marker in marker_set.get("markers", None):
                    if marker is not None:
                        writer.writerow(marker)
