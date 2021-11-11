<script lang="ts">
import {
  defineComponent, onMounted, ref, watchEffect,
} from '@vue/composition-api';
import { axiosInstance } from '@/api';
import {
  DockerImage, Algorithm, Task, Dataset,
} from '@/types';

import CreateAlgorithm from './components/CreateAlgorithm.vue';
import CreateDataset from './components/CreateDataset.vue';

export default defineComponent({
  name: 'Home',
  components: {
    CreateAlgorithm,
    CreateDataset,
  },
  setup(props, ctx) {
    const router = ctx.root.$router;
    function viewAlgorithm(id: number) {
      router.push({ name: 'algorithm', params: { id: id.toString() } });
    }

    const datasets = ref<Dataset[]>([]);
    const datasetDialogOpen = ref(false);
    const fetchDatasets = async () => {
      const res = await axiosInstance.get('datasets/');
      datasets.value = res.data.results;
    };
    const datasetCreated = () => {
      datasetDialogOpen.value = false;
      fetchDatasets();
    };

    const dockerImages = ref<DockerImage[]>([]);
    // const dockerImageDialogOpen = ref(false);
    const fetchDockerImages = async () => {
      const res = await axiosInstance.get('docker_images/');
      dockerImages.value = res.data.results;
    };

    const algorithms = ref<Algorithm[]>([]);
    const algorithmDialogOpen = ref(false);
    const fetchAlgortihms = async () => {
      const res = await axiosInstance.get('algorithms/');
      algorithms.value = res.data.results;
    };

    onMounted(() => {
      fetchDatasets();
      fetchDockerImages();
      fetchAlgortihms();
    });

    return {
      datasets,
      datasetCreated,
      datasetDialogOpen,
      dockerImages,
      algorithms,
      algorithmDialogOpen,
      viewAlgorithm,
    };
  },
});
</script>

<template>
  <v-container
    fill-height
    style="align-items: start"
  >
    <v-row style="height: 100%; max-height: 100%">
      <v-col cols="4">
        <v-card
          flat
          outlined
          style="height: 100%"
        >
          <v-card-title>Docker Images</v-card-title>
          <v-list>
            <v-list-item
              v-for="image in dockerImages"
              :key="image.id"
              class="my-2"
            >
              <v-card width="100%">
                <v-card-title>{{ image.name }}</v-card-title>
                <v-card-text>
                  Image ID: {{ image.image_id }}<br>
                  Image file: {{ image.image_file || 'null' }}<br>
                  <!-- Uses GPU: {{ alg.gpu }}<br> -->
                </v-card-text>
              </v-card>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="4">
        <v-card
          flat
          outlined
          style="height: 100%"
        >
          <v-card-title>
            Datasets
            <v-dialog
              v-model="datasetDialogOpen"
              width="50vw"
            >
              <template v-slot:activator="{ on }">
                <v-btn
                  icon
                  right
                  small
                  v-on="on"
                >
                  <v-icon color="success">
                    mdi-plus-circle
                  </v-icon>
                </v-btn>
              </template>
              <create-dataset @created="datasetCreated" />
            </v-dialog>
          </v-card-title>
          <v-list dense>
            <v-list-item
              v-for="ds in datasets"
              :key="ds.id"
              class="my-2"
              dense
            >
              <v-card
                width="100%"
              >
                <v-card-title>{{ ds.name }}</v-card-title>
                <v-card-text>
                  Number of files: {{ ds.files.length }}
                </v-card-text>
              </v-card>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="4">
        <v-card
          flat
          outlined
          style="height: 100%"
        >
          <v-card-title>
            Algorithms
            <v-dialog
              v-model="algorithmDialogOpen"
              width="50vw"
            >
              <template v-slot:activator="{ on }">
                <v-btn
                  icon
                  right
                  small
                  v-on="on"
                >
                  <v-icon color="success">
                    mdi-plus-circle
                  </v-icon>
                </v-btn>
              </template>
              <create-algorithm />
            </v-dialog>
          </v-card-title>
          <v-list dense>
            <v-list-item
              v-for="alg in algorithms"
              :key="alg.id"
              class="my-2"
              dense
            >
              <v-card
                width="100%"
                @click="viewAlgorithm(alg.id)"
              >
                <v-card-title>{{ alg.name }}</v-card-title>
                <v-card-text>
                  Command: "{{ alg.command }}"<br>
                  Uses GPU: {{ alg.gpu }}<br>

                  <!-- TODO: Num files -->
                  <!-- TODO: Num tasks -->
                  <!-- TODO: Currently running tasks (bool) -->
                </v-card-text>
              </v-card>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
