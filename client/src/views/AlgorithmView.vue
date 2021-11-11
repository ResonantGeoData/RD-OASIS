<script lang="ts">
import {
  defineComponent, ref, onMounted, computed, watch,
} from '@vue/composition-api';
import VJsoneditor from 'v-jsoneditor';

import { axiosInstance } from '@/api';
import { Algorithm, ChecksumFile, Task } from '@/types';
import UploadDialog from '@/components/UploadDialog.vue';

const fileTableHeaders = [
  {
    text: 'Name',
    align: 'start',
    value: 'name',
  },
  {
    text: 'Type (File/Url)',
    value: 'type',
  },
  {
    text: 'Download Url',
    value: 'download_url',
  },
];

export default defineComponent({
  name: 'AlgorithmView',
  components: {
    VJsoneditor,
    UploadDialog,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    // /////////////////
    // Algorithm
    // /////////////////
    const algorithm = ref<Algorithm>();
    const showAlgorithmDetails = ref(false);
    const fetchingAlgorithm = ref(false);

    async function fetchAlgorithm() {
      fetchingAlgorithm.value = true;

      try {
        const res = await axiosInstance.get(`algorithms/${props.id}/`);
        algorithm.value = res.data;
      } catch (error) {
        // TODO: Handle
      }

      fetchingAlgorithm.value = false;
    }

    async function saveAlgorithm() {
      fetchingAlgorithm.value = true;

      try {
        const res = await axiosInstance.put(`algorithms/${props.id}/`, algorithm.value);
        algorithm.value = res.data;
      } catch (error) {
        // TODO: Handle
      }

      fetchingAlgorithm.value = false;
    }

    // /////////////////
    // Tasks
    // /////////////////
    const tasks = ref<Task[]>([]);
    const selectedTaskIndex = ref<number | null>(null);
    const selectedTask = computed(() => (
      selectedTaskIndex.value !== null ? tasks.value[selectedTaskIndex.value] : null
    ));

    function fetchTasks() {
      axiosInstance.get(`algorithms/${props.id}/tasks/`).then((res) => {
        tasks.value = res.data.results.sort(
          (a: Algorithm, b: Algorithm) => -a.created.localeCompare(b.created),
        );

        // Set default to most recent, if there are any
        if (tasks.value.length) {
          selectedTaskIndex.value = 0;
        }
      });
    }

    function taskStatusIconStyle(task: Task): {icon: string; color: string} {
      switch (task.status) {
        case 'created':
        case 'queued':
          return { icon: 'mdi-pause', color: '' };
        case 'running':
          return { icon: 'mdi-sync', color: 'primary' };
        case 'success':
          return { icon: 'mdi-check', color: 'success' };
        case 'failed':
          return { icon: 'mdi-close', color: 'error' };
        default:
          return { icon: 'mdi-help', color: 'warning' };
      }
    }

    // /////////////////
    // Selected Task
    // /////////////////
    const selectedTaskLogs = ref('');
    async function fetchSelectedTaskLogs() {
      if (selectedTask.value === null) {
        return;
      }

      const res = await axiosInstance.get(`algorithm_tasks/${selectedTask.value.id}/logs/`);
      selectedTaskLogs.value = res.data;
    }

    const selectedTaskFiles = ref<{}[]>([]);
    async function fetchSelectedTaskOutput() {
      if (selectedTask.value === null) {
        return;
      }

      const res = await axiosInstance.get(`algorithm_tasks/${selectedTask.value.id}/output/`);
      selectedTaskFiles.value = res.data.results;
    }

    const selectedTaskInput = ref<ChecksumFile[]>([]);
    const fetchingSelectedTaskInput = ref(false);
    async function fetchSelectedTaskInput() {
      if (selectedTask.value === null) {
        return;
      }

      fetchingSelectedTaskInput.value = true;
      try {
        const res = await axiosInstance.get(`algorithm_tasks/${selectedTask.value.id}/input/`);
        selectedTaskInput.value = res.data.results;
      } catch (error) {
        // TODO: Handle
      }

      fetchingSelectedTaskInput.value = false;
    }

    watch(selectedTask, () => {
      fetchSelectedTaskLogs();
      fetchSelectedTaskInput();
      fetchSelectedTaskOutput();
    });

    // /////////////////
    // Misc
    // /////////////////

    // TODO: Update to include selected dataset
    async function runAlgorithm() {
      const res = await axiosInstance.post(`algorithms/${props.id}/run/`);
      if (res.status === 200) {
        fetchTasks();
      }
    }

    onMounted(() => {
      fetchAlgorithm();
      fetchTasks();
    });

    return {
      fileTableHeaders,
      algorithm,
      showAlgorithmDetails,
      fetchingAlgorithm,
      fetchAlgorithm,
      saveAlgorithm,
      selectedTaskInput,
      fetchingSelectedTaskInput,
      fetchSelectedTaskInput,
      tasks,
      taskStatusIconStyle,
      selectedTask,
      selectedTaskIndex,
      selectedTaskLogs,
      selectedTaskFiles,
      runAlgorithm,
    };
  },
});
</script>

<template>
  <v-container
    fluid
    fill-height
    style="align-items: start"
  >
    <v-row no-gutters>
      <v-col class="pa-0">
        <v-toolbar extension-height="400">
          <v-progress-circular
            v-if="!algorithm"
            indeterminate
          />
          <template v-else>
            <v-btn
              icon
              left
              @click="showAlgorithmDetails = !showAlgorithmDetails"
            >
              <v-icon v-if="showAlgorithmDetails">
                mdi-chevron-down
              </v-icon>
              <v-icon v-else>
                mdi-chevron-right
              </v-icon>
            </v-btn>
            <v-toolbar-title>
              {{ algorithm.name }} ({{ algorithm.id }})
            </v-toolbar-title>
          </template>
          <template
            v-if="showAlgorithmDetails"
            v-slot:extension
          >
            <v-card
              flat
              width="100%"
            >
              <v-card-text>
                <v-jsoneditor
                  v-model="algorithm"
                  :options="{mode: 'code', mainMenuBar: false}"
                  style="height: 300px;"
                />
              </v-card-text>
              <v-card-actions>
                <v-btn
                  :loading="fetchingAlgorithm"
                  @click="fetchAlgorithm"
                >
                  Reset
                </v-btn>
                <v-btn
                  color="primary"
                  :loading="fetchingAlgorithm"
                  @click="saveAlgorithm"
                >
                  <v-icon left>
                    mdi-content-save
                  </v-icon>
                  Save
                </v-btn>
              </v-card-actions>
            </v-card>
          </template>
        </v-toolbar>
      </v-col>
    </v-row>
    <v-row style="height: 100%">
      <v-col
        cols="auto"
        class="pa-0"
      >
        <v-navigation-drawer width="300">
          <v-list-item>
            <v-list-item-content>
              <v-list-item-title class="text-h6">
                <v-row
                  no-gutters
                  align="center"
                >
                  Tasks
                  <v-spacer />
                  <v-btn
                    class="my-1"
                    @click="runAlgorithm"
                  >
                    New Task
                    <v-icon right>
                      mdi-rocket-launch
                    </v-icon>
                  </v-btn>
                </v-row>
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
          <v-divider />
          <v-list-item v-if="!tasks.length">
            <v-list-item-content>
              <v-list-item-subtitle>
                This algorithm has no tasks...
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
          <v-list v-else>
            <!-- FIXME: For some reason, displays wrong selected after update -->
            <v-list-item-group
              v-model="selectedTaskIndex"
              color="primary"
              mandatory
            >
              <v-list-item
                v-for="task in tasks"
                :key="task.id"
              >
                {{ task.created }}
                <v-icon
                  :color="taskStatusIconStyle(task).color"
                  right
                >
                  {{ taskStatusIconStyle(task).icon }}
                </v-icon>
              </v-list-item>
            </v-list-item-group>
          </v-list>
        </v-navigation-drawer>
      </v-col>

      <v-col class="pa-0">
        <v-row no-gutters>
          <v-col>
            <v-sheet>
              <v-card-title>
                Input Dataset
              </v-card-title>
              <v-divider />
              <v-data-table
                :headers="fileTableHeaders"
                :items="selectedTaskInput"
                :loading="fetchingSelectedTaskInput"
              >
                <!-- eslint-disable-next-line vue/valid-v-slot -->
                <template v-slot:item.type="{ item }">
                  {{ item.type === 1 ? 'File' : 'Url' }}
                </template>
                <!-- eslint-disable-next-line vue/valid-v-slot -->
                <template v-slot:item.download_url="{ item }">
                  <a
                    :href="item.download_url"
                    target="_blank"
                  >
                    <span>Download</span>
                  </a>
                  <v-icon
                    small
                    class="mb-1"
                  >
                    mdi-open-in-new
                  </v-icon>
                </template>
              </v-data-table>
            </v-sheet>
          </v-col>
        </v-row>
        <v-row
          v-if="tasks.length"
          no-gutters
        >
          <v-col cols="6">
            <v-sheet
              height="100%"
              class="pa-2"
            >
              <v-card-title>Task Output Files</v-card-title>
              <v-divider />
              <v-card-text style="height: 100%">
                <v-data-table
                  :headers="fileTableHeaders"
                  :items="selectedTaskFiles"
                  item-key="id"
                  height="100%"
                >
                  <!-- eslint-disable-next-line vue/valid-v-slot -->
                  <template v-slot:item.type="{ item }">
                    {{ item.type === 1 ? 'File' : 'Url' }}
                  </template>
                  <!-- eslint-disable-next-line vue/valid-v-slot -->
                  <template v-slot:item.download_url="{ item }">
                    <a
                      :href="item.download_url"
                      target="_blank"
                    >
                      <span>Download</span>
                    </a>
                    <v-icon
                      small
                      class="mb-1"
                    >
                      mdi-open-in-new
                    </v-icon>
                  </template>
                </v-data-table>
              </v-card-text>
            </v-sheet>
          </v-col>
          <v-col cols="6">
            <v-sheet
              height="100%"
              class="pa-2"
            >
              <v-card-title>Task Output Log</v-card-title>

              <v-divider />
              <v-card-text>
                <v-textarea
                  outlined
                  readonly
                  :value="selectedTaskLogs"
                  fill-height
                  placeholder="This task has no output log..."
                  hide-details
                />
              </v-card-text>
            </v-sheet>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>
