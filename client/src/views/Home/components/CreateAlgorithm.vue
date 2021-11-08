<script lang="ts">
import { axiosInstance } from '@/api';
import { ChecksumFile, DockerImage } from '@/types';
import {
  computed, defineComponent, onMounted, ref,
} from '@vue/composition-api';
import axios from 'axios';
import VJsoneditor from 'v-jsoneditor';

export default defineComponent({
  name: 'CreateAlgorithm',
  components: {
    VJsoneditor,
  },
  setup(props, ctx) {
    const router = ctx.root.$router;

    const name = ref('');
    const command = ref('');
    const entrypoint = ref<string | null>(null);
    const gpu = ref(true);
    const dockerImage = ref<DockerImage | null>(null);
    const inputDataset = ref([] as ChecksumFile[]);
    const environment = ref({});

    const nonEmptyRule = (val: unknown) => (!!val || 'This field is required');
    const formValid = ref(false);
    const customFormFieldsValid = computed(() => (
      dockerImage.value !== null && inputDataset.value.length
    ));
    const allFieldsValid = computed(() => formValid.value && customFormFieldsValid.value);

    const dockerImageHeaders = [{ text: 'Name', value: 'name' }, { text: 'Image ID', value: 'image_id' }];
    const dockerImageList = ref<DockerImage[]>([]);

    const fileListHeaders = [{ text: 'Name', value: 'name' }, { text: 'Type (File/Url)', value: 'type' }];
    const fileList = ref<ChecksumFile[]>([]);
    onMounted(async () => {
      // TODO: Deal with server pagination
      const dockerImageRes = await axiosInstance.get('docker_images/');
      dockerImageList.value = dockerImageRes.data.results;

      // TODO: Deal with server pagination
      const fileRes = await axiosInstance.get('rgd/checksum_file');
      fileList.value = fileRes.data.results;
    });

    function resetForm() {
      name.value = '';
      command.value = '';
      entrypoint.value = null;
      gpu.value = true;
      dockerImage.value = null;
      inputDataset.value = [];
      environment.value = {};
    }

    async function createAlgorithm() {
      if (dockerImage.value === null || !inputDataset.value.length) {
        throw new Error('Attempted to create algorithm with empty docker image or dataset!');
      }

      const body = {
        name: name.value,
        command: command.value,
        entrypoint: entrypoint.value,
        gpu: gpu.value,
        docker_image: dockerImage.value.id,
        input_dataset: inputDataset.value.map((f) => f.id),
        environment: environment.value,
      };

      const res = await axiosInstance.post('algorithms/', body);
      if (res.status === 201) {
        router.push({ name: 'algorithm', params: { id: res.data.id.toString() } });
      }
    }

    return {
      name,
      command,
      entrypoint,
      gpu,
      dockerImage,
      inputDataset,
      environment,
      dockerImageHeaders,
      dockerImageList,
      fileListHeaders,
      fileList,
      createAlgorithm,

      // Form
      nonEmptyRule,
      formValid,
      allFieldsValid,
      resetForm,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      Create a new algorithm
      <v-spacer />
      <v-btn
        class="mx-1"
        @click="resetForm"
      >
        Reset
        <v-icon right>
          mdi-jellyfish
        </v-icon>
      </v-btn>
      <v-btn
        class="mx-1"
        color="success"
        :disabled="!allFieldsValid"
        @click="createAlgorithm"
      >
        Create
        <v-icon right>
          mdi-check
        </v-icon>
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-form v-model="formValid">
        <v-card-subtitle class="pl-0 pb-0">
          Required Fields
        </v-card-subtitle>
        <v-text-field
          v-model="name"
          label="name"
          :rules="[nonEmptyRule]"
        />
        <v-textarea
          v-model="command"
          label="Command"
          :rules="[nonEmptyRule]"
        />
        <v-dialog width="60vw">
          <template v-slot:activator="{ on }">
            <v-btn
              color="primary"
              class="mx-1"
              :outlined="!dockerImage"
              v-on="on"
            >
              Select Docker Image
              <v-icon right>
                mdi-docker
              </v-icon>
            </v-btn>
          </template>
          <v-data-table
            title="Docker Images"
            :items="dockerImageList"
            :headers="dockerImageHeaders"
            single-select
            selectable-key="id"
            show-select
            :value="dockerImage ? [dockerImage] : []"
            @input="dockerImage = $event[0] || null"
          />
        </v-dialog>
        <v-dialog width="60vw">
          <template v-slot:activator="{ on }">
            <v-btn
              color="primary"
              class="mx-1"
              :outlined="!inputDataset.length"
              v-on="on"
            >
              Select Input Data
              <v-icon right>
                mdi-file-multiple
              </v-icon>
            </v-btn>
          </template>
          <v-data-table
            v-model="inputDataset"
            title="Files"
            :items="fileList"
            :headers="fileListHeaders"
            selectable-key="id"
            show-select
          />
        </v-dialog>
        <template v-if="inputDataset.length">
          ({{ inputDataset.length }} selected)
        </template>

        <v-card-subtitle class="pl-0 pb-0">
          Optional Fields
        </v-card-subtitle>
        <v-checkbox
          v-model="gpu"
          label="Use GPU"
        />
        <v-textarea
          v-model="entrypoint"
          label="Entrypoint"
        />
        <v-subheader
          class="pl-0"
          style="height: 30px"
        >
          Environment
        </v-subheader>
        <v-jsoneditor
          v-model="environment"
          :options="{mode: 'code', mainMenuBar: false}"
        />
      </v-form>

      <!-- <v-btn>Create</v-btn> -->
    </v-card-text>
  </v-card>
</template>
