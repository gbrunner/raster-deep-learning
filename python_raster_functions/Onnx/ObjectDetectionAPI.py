'''
Copyright 2018 Esri

Licensed under the Apache License, Version 2.0 (the "License");

you may not use this file except in compliance with the License.

You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software

distributed under the License is distributed on an "AS IS" BASIS,

WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and

limitations under the License.​
'''

import os
import sys

import numpy as np
import onnx
from onnxruntime.backend.backend import OnnxRuntimeBackend as backend
from onnx import numpy_helper

prf_root_dir = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(prf_root_dir)
from Templates.TemplateBaseDetector import TemplateBaseDetector

class ChildObjectDetector(TemplateBaseDetector):
    def load_model(self, model_path):
        '''
        Fill this method to write your own model loading python code
        save it self object if you would like to reference it later.

        Tips: you can access emd information through self.json_info.

        TensorFlow example to import graph def from frozen pb file:
        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(model_path, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')
        '''
        # Todo: fill in this method to load your model
        # self.detection_graph = tf.Graph()
        # with self.detection_graph.as_default():
        #     od_graph_def = tf.GraphDef()
        #     with tf.gfile.GFile(model_path, 'rb') as fid:
        #         serialized_graph = fid.read()
        #         od_graph_def.ParseFromString(serialized_graph)
        #         tf.import_graph_def(od_graph_def, name='')
        self.model = onnx.load(model_path)

    def getParameterInfo(self, required_parameters):
        required_parameters.extend(
            [
                # Todo: add your inference parameters here
                # https://github.com/Esri/raster-functions/wiki/PythonRasterFunction#getparameterinfo
            ]
        )
        return required_parameters

    def inference(self, batch, **scalars):
        '''
        Fill this method to write your own inference python code, you can refer to the model instance that is created
        in the load_model method. Expected results format is described in the returns as below.

        :param batch: numpy array with shape (B, H, W, D), B is batch size, H, W is specified and equal to
                      ImageHeight and ImageWidth in the emd file and D is the number of bands and equal to the length
                      of ExtractBands in the emd. If BatchInference is set to False in emd, B is constant 1.
        :param scalars: inference parameters, accessed by the parameter name,
                       i.e. score_threshold=float(kwargs['score_threshold']). If you want to have more inference
                       parameters, add it to the list of the following getParameterInfo method.
        :return: bounding boxes, python list representing bounding boxes whose length is equal to B, each element is
                                 [N,4] numpy array representing [ymin, xmin, ymax, xmax] with respect to the upper left
                                 corner of the image tile.
                 scores, python list representing the score of each bounding box whose length is equal to B, each element
                         is [N,] numpy array
                 classes, python list representing the class of each bounding box whose length is equal to B, each element
                         is [N,] numpy array and its dype is np.uint8
        '''
        #Todo: fill in this method to inference your model and return bounding boxes, scores and classes

        score_threshold = float(scalars['score_threshold'])

        # Will use the batch size to ensure proper formatting of bounding boxes, scores, and classes
        batch_size = batch.shape[0]  # bounding_boxes.shape[0]

        # Initialize the bounding boxes, scores, and classes arrays
        batch_bounding_boxes, batch_scores, batch_classes = [], [], []
        batch_bb, batch_s, batch_c = [], [], []

        # Keeping the GPU Check from TensorFlow ObjectDetectionAPI here in case there is an ONNX analog of it
        #if 'PerProcessGPUMemoryFraction' in self.json_info:
        #    config.gpu_options.per_process_gpu_memory_fraction = float(self.json_info['PerProcessGPUMemoryFraction'])

        # Need to transpose the image becuase of how ArcGIS passes it to the raster function
        batch = np.transpose(batch, (0, 2, 3, 1))

        # Dimensions of the input array should be 4. Handle each image in the array.
        # Using this logic in case there is a bug in the prf_utils batching function.
        for image_np in batch:
            image_np_expanded = np.expand_dims(image_np, axis=0)
            bounding_boxes, scores, classes = list(backend.run_model(self.model, image_np_expanded))

            bounding_boxes[:, :, [0, 2]] = bounding_boxes[:, :, [0, 2]] * self.json_info['ImageHeight']
            bounding_boxes[:, :, [1, 3]] = bounding_boxes[:, :, [1, 3]] * self.json_info['ImageWidth']

            batch_bb.append(bounding_boxes)
            batch_s.append(scores)
            batch_c.append(classes)

        #if batch_size > 1:
        for batch_idx in range(batch_size):
            keep_indices = np.where(batch_s[batch_idx] > score_threshold)
            batch_bounding_boxes.append(batch_bb[batch_idx][keep_indices])
            batch_scores.append(batch_s[batch_idx][keep_indices])
            batch_classes.append(batch_c[batch_idx][keep_indices])
        #else:
        #    keep_indices = np.where(batch_s > score_threshold)
        #    batch_bounding_boxes.append(batch_bb[keep_indices])
        #    batch_scores.append(batch_s[keep_indices])
        #    batch_classes.append(batch_c[keep_indices])

        return batch_bounding_boxes, batch_scores, batch_classes
