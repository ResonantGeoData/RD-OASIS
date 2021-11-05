<script lang="ts">
import {
  defineComponent, reactive, ref,
} from '@vue/composition-api';

export default defineComponent({
  name: 'CreateAlgorithm',
  setup() {
    const name = ref('');
    const command = ref('');
    const entrypoint = ref<string | null>(null);
    const gpu = ref(true);
    const dockerImage = ref<number | null>(null);
    const inputDataset = ref([] as number[]);
    const environment = reactive({});
    const formValid = ref(false);

    return {
      name,
      command,
      entrypoint,
      gpu,
      dockerImage,
      inputDataset,
      environment,
      formValid,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>Create a new algorithm</v-card-title>
    <v-card-text>
      <v-form v-model="formValid">
        <v-card-subtitle class="pl-0 pb-0">
          Required Fields
        </v-card-subtitle>
        <v-text-field
          v-model="name"
          label="name"
        />
        <v-textarea
          v-model="command"
          label="Command"
        />
        <v-dialog width="60vw">
          <template v-slot:activator="{ on }">
            <v-btn
              color="primary"
              class="mx-1"
              v-on="on"
            >
              Select Docker Image
              <v-icon right>
                mdi-docker
              </v-icon>
            </v-btn>
          </template>
          <!-- TODO: Finish-->
          <v-data-table
            :items="[1, 2, 3]"
            title="asd"
          />
        </v-dialog>
        <v-dialog width="60vw">
          <template v-slot:activator="{ on }">
            <v-btn
              color="primary"
              class="mx-1"
              v-on="on"
            >
              Select Input Data
              <v-icon right>
                mdi-file-multiple
              </v-icon>
            </v-btn>
          </template>
          <!-- TODO: Finish-->
          <v-data-table
            :items="[1, 2, 3]"
            title="asd"
          />
        </v-dialog>

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
        <v-textarea
          v-model="environment"
          label="Environment"
        />
      </v-form>
    </v-card-text>
  </v-card>
</template>
