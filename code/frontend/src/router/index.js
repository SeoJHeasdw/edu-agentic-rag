import { createRouter, createWebHistory } from "vue-router";
import ChatView from "@/views/ChatView.vue";
import ManageView from "@/views/ManageView.vue";

const routes = [
    {
        path: "/",
        name: "home",
        component: ChatView,
    },
    {
        path: "/chat",
        name: "chat",
        component: ChatView,
    },
    {
        path: "/manage",
        name: "manage",
        component: ManageView,
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

export default router;

