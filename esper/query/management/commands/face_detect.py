from django.core.management.base import BaseCommand, CommandError
from query.models import Video, Face
from scannerpy import Database, DeviceType, Job
from scannerpy.stdlib import parsers, pipelines
import os
import cv2

class Command(BaseCommand):
    help = 'Detect faces in videos'

    def add_arguments(self, parser):
        parser.add_argument('path')

    def handle(self, *args, **options):
        with open(options['path']) as f:
            paths = [s.strip() for s in f.readlines()]

        with Database() as db:
            filtered = []
            for path in paths:
                video = Video.objects.filter(path=path)
                if len(video) == 0: continue
                video = video[0]
                if len(Face.objects.filter(video=video)) > 0: continue
                filtered.append(path)

            c = db.new_collection('tmp', filtered, force=True)
            faces_c = pipelines.detect_faces(
                db, c, lambda t: t.all(), 'tmp_faces')

            for path, video_faces_table in zip(filtered, faces_c.tables()):
                video = Video.objects.filter(path=path).get()
                frames = db.table(path).load(['frame'])
                video_faces = video_faces_table.load(['bboxes'], parsers.bboxes)
                for (i, frame_faces), (_, frame) in zip(video_faces, frames):
                    for bbox in frame_faces:
                        f = Face()
                        f.video = video
                        f.frame = i
                        f.bbox = bbox
                        f.save()

                        thumbnail_path = 'assets/thumbnails/{}_{}.jpg'.format(video.id, f.id)
                        thumbnail = frame[0][int(bbox.y1):int(bbox.y2),
                                             int(bbox.x1):int(bbox.x2)]
                        cv2.imwrite(thumbnail_path, cv2.cvtColor(thumbnail, cv2.COLOR_RGB2BGR))
