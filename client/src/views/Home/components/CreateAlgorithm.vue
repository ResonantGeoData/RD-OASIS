<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import VJsoneditor from 'v-jsoneditor';

export default defineComponent({
  name: 'CreateAlgorithm',
  components: {
    VJsoneditor,
  },
  setup() {
    const name = ref('');
    const command = ref('');
    const entrypoint = ref<string | null>(null);
    const gpu = ref(true);
    const dockerImage = ref<number | null>(null);
    const inputDataset = ref([] as number[]);
    const environment = ref({});

    const nonEmptyRule = (val: unknown) => (!!val || 'This field is required');
    const formValid = ref(false);
    const customFormFieldsValid = computed(() => (
      dockerImage.value !== null && inputDataset.value.length
    ));
    const allFieldsValid = computed(() => formValid.value && customFormFieldsValid.value);

    function resetForm() {
      name.value = '';
      command.value = '';
      entrypoint.value = null;
      gpu.value = true;
      dockerImage.value = null;
      inputDataset.value = [];
      environment.value = {};
    }

    return {
      name,
      command,
      entrypoint,
      gpu,
      dockerImage,
      inputDataset,
      environment,

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
