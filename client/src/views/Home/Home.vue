<script lang="ts">
import {
  defineComponent, ref, watchEffect,
} from '@vue/composition-api';
import { axiosInstance } from '@/api';
import { DockerImage, Algorithm, Task } from '@/types';

import CreateAlgorithm from './components/CreateAlgorithm.vue';

export default defineComponent({
  name: 'Home',
  components: {
    CreateAlgorithm,
  },
  setup(props, ctx) {
    const router = ctx.root.$router;
    function viewAlgorithm(id: number) {
      router.push({ name: 'algorithm', params: { id: id.toString() } });
    }

    const dockerImages = ref<DockerImage[]>([]);
    axiosInstance.get('docker_images/').then((res) => {
      dockerImages.value = res.data.results;
    });

    const algorithms = ref<Algorithm[]>([]);
    axiosInstance.get('algorithms/').then((res) => {
      algorithms.value = res.data.results;
    });

    const selectedAlgorithm = ref<Algorithm | null>(null);
    const tasks = ref<Task[] | null>(null);
    watchEffect(async () => {
      if (selectedAlgorithm.value === null) {
        tasks.value = null;
        return;
      }

      const res = await axiosInstance.get(`algorithms/${selectedAlgorithm.value.id}/tasks/`);
      tasks.value = res.data.results.sort(
        (a: Algorithm, b: Algorithm) => -a.created.localeCompare(b.created),
      );
    });

    return {
      dockerImages,
      algorithms,
      selectedAlgorithm,
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
      <v-col cols="6">
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
      <v-col cols="6">
        <v-card
          flat
          outlined
          style="height: 100%"
        >
          <v-card-title>
            Algorithms
            <v-dialog width="50vw">
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
                </v-card-text>
              </v-card>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
