<script lang="ts">
import {
  defineComponent, ref, watchEffect, onMounted,
} from '@vue/composition-api';
import { axiosInstance } from '@/api';
import { Algorithm, Task } from '@/types';

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
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const algorithm = ref<Algorithm>();
    const tasks = ref<Task[]>([]);
    onMounted(async () => {
      algorithm.value = (await axiosInstance.get(`algorithms/${props.id}/`)).data;
      tasks.value = (await axiosInstance.get(`algorithms/${props.id}/tasks/`)).data.results.sort(
        (a: Algorithm, b: Algorithm) => -a.created.localeCompare(b.created),
      );
    });

    const selectedTask = ref<Task | null>(null);
    const selectedTaskLogs = ref('');
    const selectedTaskFiles = ref<{}[]>([]);
    watchEffect(async () => {
      if (selectedTask.value === null) {
        return;
      }

      const taskUrl = `algorithms/${props.id}/tasks/${selectedTask.value.id}`;
      selectedTaskLogs.value = (await axiosInstance.get(`${taskUrl}/logs/`)).data;
      selectedTaskFiles.value = (await axiosInstance.get(`${taskUrl}/output/`)).data.results;
    });

    return {
      fileTableHeaders,
      algorithm,
      tasks,
      selectedTask,
      selectedTaskLogs,
      selectedTaskFiles,
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
    <v-row style="height: 100%">
      <v-col
        cols="auto"
        class="pa-0"
      >
        <v-navigation-drawer>
          <v-list-item>
            <v-list-item-content>
              <v-list-item-title class="text-h6">
                Tasks
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
          <v-divider />

          <v-list>
            <v-list-item-group
              color="primary"
              @change="selectedTask = tasks[$event]"
            >
              <v-list-item
                v-for="task in tasks"
                :key="task.id"
              >
                {{ task.id }}
              </v-list-item>
            </v-list-item-group>
          </v-list>
        </v-navigation-drawer>
      </v-col>
      <v-col class="pa-0">
        <v-row
          style="height: 100%"
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
