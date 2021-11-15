<script lang="ts">
import { defineComponent, ref } from '@vue/composition-api';

import { axiosInstance } from '@/api';
import UploadDialog from '@/components/UploadDialog.vue';

export default defineComponent({
  name: 'CreateDockerImage',
  components: {
    UploadDialog,
  },
  setup(props, ctx) {
    const name = ref('');
    const imageId = ref('');

    async function createDockerImage() {
      if (!(name.value && imageId.value)) {
        throw new Error('Attempted to create dataset with empty name or image id!');
      }

      const body = {
        name: name.value,
        // eslint-disable-next-line @typescript-eslint/camelcase
        image_id: imageId.value,
      };

      const res = await axiosInstance.post('docker_images/', body);
      if (res.status === 201) {
        ctx.emit('created', res.data);

        // Clear data
        name.value = '';
        imageId.value = '';
      }
    }

    return {
      name,
      imageId,
      createDockerImage,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      Create a new Docker Image
      <v-spacer />
      <v-btn
        class="mx-1"
        color="success"
        :disabled="!(name && imageId)"
        @click="createDockerImage"
      >
        Create
        <v-icon right>
          mdi-plus
        </v-icon>
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-text-field
        v-model="name"
        label="Name"
        :rules="[(val) => (!!val || 'This field is required')]"
      />
      <v-text-field
        v-model="imageId"
        label="Image ID"
        :rules="[(val) => (!!val || 'This field is required')]"
      />
    </v-card-text>
  </v-card>
</template>
