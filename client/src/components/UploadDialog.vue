<script lang="ts">
import { uploadFiles } from '@/utils/upload';
import { defineComponent, ref } from '@vue/composition-api';
import VJsoneditor from 'v-jsoneditor';

export default defineComponent({
  name: 'CreateAlgorithm',
  components: {
    VJsoneditor,
  },
  setup(props, ctx) {
    const files = ref<File[]>([]);
    const uploading = ref(false);
    async function upload() {
      uploading.value = true;
      await uploadFiles(files.value);
      uploading.value = false;

      ctx.emit('complete');
    }

    return {
      files,
      upload,
      uploading,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      Upload Data
    </v-card-title>
    <v-progress-linear
      v-if="uploading"
      indeterminate
    />
    <v-card-text>
      <v-file-input
        v-model="files"
        multiple
        clearable
      />
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        :disabled="!files.length"
        color="primary"
        @click="upload"
      >
        Upload
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
