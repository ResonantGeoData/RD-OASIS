<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { oauthClient } from '@/api';

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

    return {
      loginText,
      logInOrOut,
    };
  },
});
</script>

<template>
  <v-app>
    <!-- For some reason, flex-grow-0 is needed or the app-bar is huge -->
    <v-app-bar class="flex-grow-0">
      <v-app-bar-title>OASIS</v-app-bar-title>
      <v-spacer />
      <v-btn
        text
        @click="logInOrOut"
      >
        {{ loginText }}
      </v-btn>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
