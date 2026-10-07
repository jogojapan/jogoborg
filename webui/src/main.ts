import './styles.css';
import { mount } from 'svelte';
import App from './App.svelte';
import { initialize } from './lib/auth.svelte';

const target = document.getElementById('app');
if (!target) throw new Error('App mount point #app not found');

mount(App, { target });
initialize();