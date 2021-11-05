import Vue from 'vue';
import VueRouter, { RouteConfig } from 'vue-router';
import Home from '@/views/Home.vue';
import AlgorithmView from '@/views/AlgorithmView.vue';

Vue.use(VueRouter);

const routes: Array<RouteConfig> = [
  {
    path: '/algorithm/:id',
    component: AlgorithmView,
    name: 'algorithm',
    props: true,
  },
  {
    path: '/',
    component: Home,
  },
];

const router = new VueRouter({
  routes,
});

export default router;
