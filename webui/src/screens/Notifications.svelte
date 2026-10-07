<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, toastSuccess, errMsg } from '../lib/toast.svelte';
  import type { NotificationSettings } from '../lib/types';
  import Icon from '../components/Icon.svelte';

  let loading = $state(true);
  let savingSmtp = $state(false);
  let savingWebhook = $state(false);
  let testingSmtp = $state(false);
  let testingWebhook = $state(false);

  let smtpHost = $state('');
  let smtpPort = $state('587');
  let smtpUsername = $state('');
  let smtpPassword = $state('');
  let smtpSender = $state('');
  let smtpRecipient = $state('');
  let smtpSecurity = $state('STARTTLS');

  let webhookUrl = $state('');
  let webhookToken = $state('');
  let successPriority = $state('normal');
  let errorPriority = $state('high');

  async function load() {
    loading = true;
    try {
      const res = await api.get<{ settings: NotificationSettings }>(
        '/notifications/edit',
        auth.token
      );
      const s = res.settings ?? {};
      const smtp = s.smtp_config ?? {};
      const web = s.webhook_config ?? {};
      smtpHost = smtp.host ?? '';
      smtpPort = String(smtp.port ?? 587);
      smtpUsername = smtp.username ?? '';
      smtpPassword = smtp.password ?? '';
      smtpSender = smtp.sender_email ?? '';
      smtpRecipient = smtp.recipient_email ?? '';
      smtpSecurity = smtp.security ?? 'STARTTLS';
      webhookUrl = web.url ?? '';
      webhookToken = web.token ?? '';
      successPriority = web.success_priority ?? 'normal';
      errorPriority = web.error_priority ?? 'high';
    } catch (e) {
      toastError('Failed to load notification settings: ' + errMsg(e));
    } finally {
      loading = false;
    }
  }

  function fullSettings(): NotificationSettings {
    return {
      smtp_config: {
        host: smtpHost,
        port: Number(smtpPort) || 587,
        username: smtpUsername,
        password: smtpPassword,
        sender_email: smtpSender,
        recipient_email: smtpRecipient,
        security: smtpSecurity,
      },
      webhook_config: {
        url: webhookUrl,
        token: webhookToken,
        success_priority: successPriority,
        error_priority: errorPriority,
      },
    };
  }

  async function saveSmtp() {
    savingSmtp = true;
    try {
      await api.put('/notifications', fullSettings(), auth.token);
      toastSuccess('SMTP settings saved');
    } catch (e) {
      toastError('Failed to save SMTP settings: ' + errMsg(e));
    } finally {
      savingSmtp = false;
    }
  }

  async function saveWebhook() {
    savingWebhook = true;
    try {
      await api.put('/notifications', fullSettings(), auth.token);
      toastSuccess('Webhook settings saved');
    } catch (e) {
      toastError('Failed to save webhook settings: ' + errMsg(e));
    } finally {
      savingWebhook = false;
    }
  }

  async function testSmtp() {
    testingSmtp = true;
    const smtp = fullSettings().smtp_config ?? {};
    try {
      await api.post('/notifications/test/smtp', smtp, auth.token);
      toastSuccess('SMTP test successful!');
    } catch (e) {
      toastError('SMTP test failed: ' + errMsg(e));
    } finally {
      testingSmtp = false;
    }
  }

  async function testWebhook() {
    testingWebhook = true;
    try {
      await api.post(
        '/notifications/test/webhook',
        { url: webhookUrl, token: webhookToken, priority: 'normal' },
        auth.token
      );
      toastSuccess('Webhook test successful!');
    } catch (e) {
      toastError('Webhook test failed: ' + errMsg(e));
    } finally {
      testingWebhook = false;
    }
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

{#if loading}
  <div class="spinner"></div>
{:else}
  <div class="grid">
    <section class="card">
      <h3><Icon icon="email" /> SMTP Configuration</h3>
      <div class="grid cols-2">
        <div class="field">
          <label for="smtp-host">Host</label>
          <input id="smtp-host" bind:value={smtpHost} />
        </div>
        <div class="field">
          <label for="smtp-port">Port</label>
          <input id="smtp-port" type="number" bind:value={smtpPort} />
        </div>
        <div class="field">
          <label for="smtp-security">Security</label>
          <select id="smtp-security" bind:value={smtpSecurity}>
            <option value="STARTTLS">STARTTLS</option>
            <option value="SSL">SSL/TLS</option>
            <option value="None">None</option>
          </select>
        </div>
        <div class="field">
          <label for="smtp-user">Username</label>
          <input id="smtp-user" bind:value={smtpUsername} />
        </div>
        <div class="field">
          <label for="smtp-pass">Password</label>
          <input id="smtp-pass" type="password" bind:value={smtpPassword} />
        </div>
        <div class="field">
          <label for="smtp-sender">Sender Email</label>
          <input id="smtp-sender" bind:value={smtpSender} />
        </div>
        <div class="field">
          <label for="smtp-recip">Recipient Email</label>
          <input id="smtp-recip" bind:value={smtpRecipient} />
        </div>
      </div>
      <div class="actions">
        <button class="btn" onclick={saveSmtp} disabled={savingSmtp}>
          {savingSmtp ? 'Saving…' : 'Save'}
        </button>
        <button class="btn ghost" onclick={testSmtp} disabled={testingSmtp}>
          <Icon icon="check" size={16} /> {testingSmtp ? 'Testing…' : 'Test'}
        </button>
      </div>
    </section>

    <section class="card">
      <h3><Icon icon="webhook" /> Webhook (Gotify)</h3>
      <div class="grid cols-2">
        <div class="field full">
          <label for="webhook-url">URL</label>
          <input id="webhook-url" bind:value={webhookUrl} placeholder="https://gotify.example.com/message" />
        </div>
        <div class="field">
          <label for="webhook-token">Token</label>
          <input id="webhook-token" type="password" bind:value={webhookToken} />
        </div>
        <div class="field">
          <label for="webhook-spri">Success Priority</label>
          <select id="webhook-spri" bind:value={successPriority}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
        </div>
        <div class="field">
          <label for="webhook-epri">Error Priority</label>
          <select id="webhook-epri" bind:value={errorPriority}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>
      <div class="actions">
        <button class="btn" onclick={saveWebhook} disabled={savingWebhook}>
          {savingWebhook ? 'Saving…' : 'Save'}
        </button>
        <button class="btn ghost" onclick={testWebhook} disabled={testingWebhook}>
          <Icon icon="check" size={16} /> {testingWebhook ? 'Testing…' : 'Test'}
        </button>
      </div>
    </section>
  </div>
{/if}

<style>
  h3 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
  }
  .full {
    grid-column: 1 / -1;
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 6px;
  }
</style>