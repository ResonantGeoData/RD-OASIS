<script lang="ts">
import {
  defineComponent, computed, ref, watchEffect,
} from '@vue/composition-api';
import { axiosInstance, oauthClient } from '@/api';
import { DockerImage, Algorithm, Task } from '@/types';

export default defineComponent({
  setup() {
    const loginText = computed(() => (oauthClient.isLoggedIn ? 'Logout' : 'Login'));
    const logInOrOut = () => {
      if (oauthClient.isLoggedIn) {
        oauthClient.logout();
      } else {
        oauthClient.redirectToLogin();
      }
    };

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
      loginText,
      logInOrOut,
      dockerImages,
      algorithms,
      selectedAlgorithm,
      tasks,
    };
  },
});
</script>

<template>
  <div>
    <v-toolbar>
      <v-toolbar-title>OASIS</v-toolbar-title>
      <v-spacer />
      <v-btn
        text
        @click="logInOrOut"
      >
        {{ loginText }}
      </v-btn>
    </v-toolbar>
    <v-container>
      <v-row>
        <v-col cols="4">
          <v-card>
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
        <v-col cols="4">
          <v-card>
            <v-card-title>Algorithms</v-card-title>
            <v-list dense>
              <v-list-item
                v-for="alg in algorithms"
                :key="alg.id"
                class="my-2"
                dense
              >
                <v-card
                  width="100%"
                  @click="selectedAlgorithm = alg"
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
        <v-col cols="4">
          <v-card>
            <v-card-title>
              {{
                selectedAlgorithm === null
                  ? 'Select an algorithm to view its tasks'
                  : `Tasks for ${selectedAlgorithm.name}`
              }}
            </v-card-title>
            <v-card-subtitle v-if="tasks && tasks.length === 0">
              This algorithm has no tasks yet...
            </v-card-subtitle>
            <v-list
              v-else
              dense
            >
              <v-list-item
                v-for="task in tasks"
                :key="task.id"
                class="my-2"
                dense
              >
                <v-card width="100%">
                  <v-card-title>
                    <v-icon
                      left
                      :color="task.status === 'success' ? 'success' : 'error'"
                    >
                      {{ task.status === 'success' ? 'mdi-check-circle' : 'mdi-close-circle' }}
                    </v-icon>
                    <span class="text-capitalize">
                      {{ task.status }}
                    </span>
                  </v-card-title>
                  <v-card-text>
                    Started: {{ task.created }}<br>
                    Finished: {{ task.modified }}<br>
                  </v-card-text>
                  <v-card-actions>
                    <v-btn>
                      <v-icon left>
                        mdi-open-in-app
                      </v-icon>
                      View Logs
                    </v-btn>
                    <v-btn>
                      <v-icon left>
                        mdi-open-in-app
                      </v-icon>
                      View Output Files
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>
