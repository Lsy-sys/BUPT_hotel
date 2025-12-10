/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import LandingPage from '../components/landing/LandingPage.vue';
import Homepage from '../components/homepage/Homepage.vue';
import MainLayout from '../components/views/MainLayout.vue';
import RoomView from '../components/views/RoomView.vue';
import AdminView from '../components/views/AdminView.vue';
import FrontDeskView from '../components/views/FrontDeskView.vue';
import ManagerView from '../components/views/ManagerView.vue';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    component: LandingPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/home',
    name: 'home',
    component: Homepage,
    meta: { requiresAuth: false }
  },
  {
    path: '/app',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/app/room'
      },
      {
        path: 'room',
        name: 'room',
        component: RoomView,
        meta: {
          requiresAuth: true,
          role: 'guest',
          title: '客房控制'
        }
      },
      {
        path: 'admin',
        name: 'admin',
        component: AdminView,
        meta: {
          requiresAuth: true,
          role: 'admin',
          title: '管理员监控'
        }
      },
      {
        path: 'frontdesk',
        name: 'frontdesk',
        component: FrontDeskView,
        meta: {
          requiresAuth: true,
          role: 'receptionist',
          title: '前台结账'
        }
      },
      {
        path: 'manager',
        name: 'manager',
        component: ManagerView,
        meta: {
          requiresAuth: true,
          role: 'manager',
          title: '统计报表'
        }
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 路由守卫（可选，根据需要启用）
// router.beforeEach((to, from, next) => {
//   // 可以在这里添加登录验证逻辑
//   next();
// });

export default router;
