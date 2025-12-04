import { createRouter, createWebHistory } from "vue-router";
import ChatView from "@/views/ChatView.vue";
import MockChatView from "@/views/MockChatView.vue";

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
        path: "/demo-chat",
        name: "demo-chat",
        component: MockChatView,
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

export default router;

