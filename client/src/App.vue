<script setup>
import { onMounted, ref } from "vue";
import WZoom from "vanilla-js-wheel-zoom";
const base_url = import.meta.env.VITE_SERVER_BASE;

// --- UI Switching ---
const uiMode = ref('bracket');

function changeUIMode(mode) {
  uiMode.value = mode;
}

// --- Preview UI ---
onMounted(() => {
  var frame = document.getElementById('preview-viewport');
  var wzoom = WZoom.create('#preview-content', {
    type: 'image',
    maxScale: 10,
    minScale: 1,
    alignContent: "center",
    onGrab: function () {
      frame.style.cursor = 'grabbing';
    },
    onDrop: function () {
      frame.style.cursor = 'grab';
    }
  });

  window.addEventListener("resize", function () {
    wzoom.prepare();
  });
});


async function previewCheckboxChanged(event) {
  if (event.srcElement.checked) {
    await fetch(`http://${base_url}:5000/camera/start_preview`);
  } else {
    await fetch(`http://${base_url}:5000/camera/stop_preview`);
  }
}

async function settingChanged(event, setting) {
  try {
    const response = await fetch(`http://${base_url}:5000/camera/set_property/${setting}?value=${event.target.value}`, {
      method: 'GET',
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log('Focus command response:', data);
  } catch (error) {
    console.error('Error sending focus command:', error);
  }
}

// --- Focus ---
const focus_enabled = ref(false);

async function sendFocusCommand(command) {
  await fetch(`http://${base_url}:5000/camera/manualfocus/${command}`);
}

// --- Camera status ---
const server_connected = ref(false);

const camera_connected = ref(false);

const batterylevel = ref("0%");

const iso = ref("0");
const shutterspeed = ref("0");
const aperture = ref("0");

const preview_capture = ref(false);

const bracket_running = ref(false);

const bracket_iso = ref("100");
const bracket_aperture = ref("6.3");
const bracket_shutterspeed_start = ref("1/1000");
const bracket_shutterspeed_stop = ref("1/60");

const intervallometer_running = ref(false);
const intervallometer_interval = ref(10);

async function fetchStatus() {
  try {
    const response = await fetch(`http://${base_url}:5000/status`);
    if (!response.ok) {
      server_connected.value = false;
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    server_connected.value = true;

    camera_connected.value = data.connected;

    batterylevel.value = data.batterylevel;

    iso.value = data.iso;
    shutterspeed.value = data.shutterspeed;
    aperture.value = data.aperture;

    preview_capture.value = data.preview_capture;
    
    bracket_running.value = data.bracket_running;

    bracket_iso.value = data.bracket_iso;
    bracket_aperture.value = data.bracket_aperture;
    bracket_shutterspeed_start.value = data.bracket_shutterspeed_start;
    bracket_shutterspeed_stop.value = data.bracket_shutterspeed_stop;

    intervallometer_running.value = data.intervallometer_running;
    intervallometer_interval.value = data.intervallometer_interval;
  } catch (error) {
    server_connected.value = false;
    console.error('Error fetching camera status:', error);
  }
}

async function bracketSettingChanged() {
  await fetch(`http://${base_url}:5000/camera/bracket?iso=${bracket_iso.value}&aperture=${bracket_aperture.value}&shutterspeed_start=${bracket_shutterspeed_start.value}&shutterspeed_stop=${bracket_shutterspeed_stop.value}`);
}

async function startBracketCapture() {
  bracketSettingChanged();
  await fetch(`http://${base_url}:5000/camera/bracket/start`);  
}

async function stopBracketCapture() {
  await fetch(`http://${base_url}:5000/camera/bracket/stop`);  
}

setInterval(fetchStatus, 1000);
</script>

<template>
  <div class="container">
    <header>
      <div class="header-item" v-if="server_connected">🌐✅</div>
      <div class="header-item" v-if="!server_connected">🌐❌</div>
      <div class="header-item" v-if="camera_connected">📷✅</div>
      <div class="header-item" v-if="!camera_connected">📷❌</div>
      <div class="header-item">🔋{{ batterylevel }}</div>
      <div class="header-item">{{ base_url }}</div>
    </header>
    <nav>
      <button :class="{ active: uiMode === 'bracket' }" @click="changeUIMode('bracket')">Bracket</button>
      <button :class="{ active: uiMode === 'preview' }" @click="changeUIMode('preview')">Preview</button>
    </nav>

    <!-- Bracket mode -->
    <main v-show="uiMode === 'bracket'">
      <section class="vertical-gaps">
        <h1>Current Bracket</h1>
        <div class="row space-around">
          <div class="labelled-dropdown-box">
            <label>ISO</label>
            <select v-model="bracket_iso" @change="bracketSettingChanged">
              <option value="Auto">Auto</option>
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="400">400</option>
              <option value="800">800</option>
              <option value="1600">1600</option>
              <option value="3200">3200</option>
              <option value="6400">6400</option>
            </select>
          </div>
          <div class="labelled-dropdown-box">
            <label>Aperture</label>
            <select v-model="bracket_aperture" @change="bracketSettingChanged">
              <option value="6.3">6.3</option>
              <option value="7.1">7.1</option>
              <option value="8">8</option>
              <option value="9">9</option>
              <option value="10">10</option>
              <option value="11">11</option>
              <option value="13">13</option>
              <option value="14">14</option>
              <option value="16">16</option>
              <option value="18">18</option>
              <option value="20">20</option>
              <option value="22">22</option>
              <option value="25">25</option>
              <option value="29">29</option>
              <option value="32">32</option>
              <option value="36">36</option>
              <option value="40">40</option>
            </select>
          </div>
        </div>
        <div class="row space-around">
          <div class="labelled-dropdown-box">
            <label>Shutterspeed start</label>
            <select v-model="bracket_shutterspeed_start" @change="bracketSettingChanged">
              <option value="30">30</option>
              <option value="25">25</option>
              <option value="20">20</option>
              <option value="15">15</option>
              <option value="13">13</option>
              <option value="10.3">10.3</option>
              <option value="8">8</option>
              <option value="6.3">6.3</option>
              <option value="5">5</option>
              <option value="4">4</option>
              <option value="3.2">3.2</option>
              <option value="2.5">2.5</option>
              <option value="2">2</option>
              <option value="1.6">1.6</option>
              <option value="1.3">1.3</option>
              <option value="1">1</option>
              <option value="0.8">0.8</option>
              <option value="0.6">0.6</option>
              <option value="0.5">0.5</option>
              <option value="0.4">0.4</option>
              <option value="0.3">0.3</option>
              <option value="1/4">1/4</option>
              <option value="1/5">1/5</option>
              <option value="1/6">1/6</option>
              <option value="1/8">1/8</option>
              <option value="1/10">1/10</option>
              <option value="1/13">1/13</option>
              <option value="1/15">1/15</option>
              <option value="1/20">1/20</option>
              <option value="1/25">1/25</option>
              <option value="1/30">1/30</option>
              <option value="1/40">1/40</option>
              <option value="1/50">1/50</option>
              <option value="1/60">1/60</option>
              <option value="1/80">1/80</option>
              <option value="1/100">1/100</option>
              <option value="1/125">1/125</option>
              <option value="1/160">1/160</option>
              <option value="1/200">1/200</option>
              <option value="1/250">1/250</option>
              <option value="1/320">1/320</option>
              <option value="1/400">1/400</option>
              <option value="1/500">1/500</option>
              <option value="1/640">1/640</option>
              <option value="1/800">1/800</option>
              <option value="1/1000">1/1000</option>
              <option value="1/1250">1/1250</option>
              <option value="1/1600">1/1600</option>
              <option value="1/2000">1/2000</option>
              <option value="1/2500">1/2500</option>
              <option value="1/3200">1/3200</option>
              <option value="1/4000">1/4000</option>
            </select>
            <label>and stop</label>
            <select v-model="bracket_shutterspeed_stop" @change="bracketSettingChanged">
              <option value="30">30</option>
              <option value="25">25</option>
              <option value="20">20</option>
              <option value="15">15</option>
              <option value="13">13</option>
              <option value="10.3">10.3</option>
              <option value="8">8</option>
              <option value="6.3">6.3</option>
              <option value="5">5</option>
              <option value="4">4</option>
              <option value="3.2">3.2</option>
              <option value="2.5">2.5</option>
              <option value="2">2</option>
              <option value="1.6">1.6</option>
              <option value="1.3">1.3</option>
              <option value="1">1</option>
              <option value="0.8">0.8</option>
              <option value="0.6">0.6</option>
              <option value="0.5">0.5</option>
              <option value="0.4">0.4</option>
              <option value="0.3">0.3</option>
              <option value="1/4">1/4</option>
              <option value="1/5">1/5</option>
              <option value="1/6">1/6</option>
              <option value="1/8">1/8</option>
              <option value="1/10">1/10</option>
              <option value="1/13">1/13</option>
              <option value="1/15">1/15</option>
              <option value="1/20">1/20</option>
              <option value="1/25">1/25</option>
              <option value="1/30">1/30</option>
              <option value="1/40">1/40</option>
              <option value="1/50">1/50</option>
              <option value="1/60">1/60</option>
              <option value="1/80">1/80</option>
              <option value="1/100">1/100</option>
              <option value="1/125">1/125</option>
              <option value="1/160">1/160</option>
              <option value="1/200">1/200</option>
              <option value="1/250">1/250</option>
              <option value="1/320">1/320</option>
              <option value="1/400">1/400</option>
              <option value="1/500">1/500</option>
              <option value="1/640">1/640</option>
              <option value="1/800">1/800</option>
              <option value="1/1000">1/1000</option>
              <option value="1/1250">1/1250</option>
              <option value="1/1600">1/1600</option>
              <option value="1/2000">1/2000</option>
              <option value="1/2500">1/2500</option>
              <option value="1/3200">1/3200</option>
              <option value="1/4000">1/4000</option>
            </select>
          </div>
        </div>
        <div class="row">
          <button class="big-action-button" v-if="!bracket_running" @click="startBracketCapture()">Capture bracket</button>
          <button class="big-action-button active" v-if="bracket_running" @click="stopBracketCapture()">Stop bracket</button>
        </div>
      </section>

      <section class="vertical-gaps">
        <h1>Intervallometer</h1>
        <div class="row space-around">
          <div class="labelled-textbox">
            <label>Interval</label>
            <input type="number" v-model="intervallometer_interval"/>
          </div>
        </div>
        <div class="row">
          <button class="big-action-button" v-if="!intervallometer_running">Start</button>
          <button class="big-action-button active" v-if="intervallometer_running">Stop</button>
        </div>
      </section>

    </main>

    <!-- Preview mode -->
    <main v-show="uiMode === 'preview'">
      <section id="preview-viewport">
        <img id="preview-content" :src="'http://' + base_url + ':5000/preview_feed'" />
      </section>
      <div class="focus-button-container">
        <button :disabled="!focus_enabled" class="focus-button"
          @click="sendFocusCommand('near_3')">&lt;&lt;&lt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('near_2')">&lt;&lt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('near_1')">&lt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('far_1')">&gt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('far_2')">&gt;&gt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('far_3')">&gt;&gt;&gt;</button>
      </div>
      <section id="preview-settings-container">
        <div class="row space-around">
          <div class="labelled-checkbox">
            <label>Enable preview</label>
            <input type="checkbox" @click="previewCheckboxChanged" v-model="preview_capture" />
          </div>

          <div class="labelled-checkbox">
            <label>Enable focus</label>
            <input type="checkbox" v-model="focus_enabled" />
          </div>
        </div>
        <div class="row space-around">
          <div class="labelled-dropdown-box">
            <label>ISO</label>
            <select v-model="iso" @change="settingChanged($event, 'iso')">
              <option value="Auto">Auto</option>
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="400">400</option>
              <option value="800">800</option>
              <option value="1600">1600</option>
              <option value="3200">3200</option>
              <option value="6400">6400</option>
            </select>
          </div>



          <div class="labelled-dropdown-box">
            <label>Aperture</label>
            <select v-model="aperture" @change="settingChanged($event, 'aperture')">
              <option value="6.3">6.3</option>
              <option value="7.1">7.1</option>
              <option value="8">8</option>
              <option value="9">9</option>
              <option value="10">10</option>
              <option value="11">11</option>
              <option value="13">13</option>
              <option value="14">14</option>
              <option value="16">16</option>
              <option value="18">18</option>
              <option value="20">20</option>
              <option value="22">22</option>
              <option value="25">25</option>
              <option value="29">29</option>
              <option value="32">32</option>
              <option value="36">36</option>
              <option value="40">40</option>
            </select>
          </div>
        </div>
        <div class="row space-around">
          <div class="labelled-dropdown-box">
            <label>Shutter Speed</label>
            <select v-model="shutterspeed" @change="settingChanged($event, 'shutterspeed')">
              <option value="bulb">bulb</option>
              <option value="30">30</option>
              <option value="25">25</option>
              <option value="20">20</option>
              <option value="15">15</option>
              <option value="13">13</option>
              <option value="10.3">10.3</option>
              <option value="8">8</option>
              <option value="6.3">6.3</option>
              <option value="5">5</option>
              <option value="4">4</option>
              <option value="3.2">3.2</option>
              <option value="2.5">2.5</option>
              <option value="2">2</option>
              <option value="1.6">1.6</option>
              <option value="1.3">1.3</option>
              <option value="1">1</option>
              <option value="0.8">0.8</option>
              <option value="0.6">0.6</option>
              <option value="0.5">0.5</option>
              <option value="0.4">0.4</option>
              <option value="0.3">0.3</option>
              <option value="1/4">1/4</option>
              <option value="1/5">1/5</option>
              <option value="1/6">1/6</option>
              <option value="1/8">1/8</option>
              <option value="1/10">1/10</option>
              <option value="1/13">1/13</option>
              <option value="1/15">1/15</option>
              <option value="1/20">1/20</option>
              <option value="1/25">1/25</option>
              <option value="1/30">1/30</option>
              <option value="1/40">1/40</option>
              <option value="1/50">1/50</option>
              <option value="1/60">1/60</option>
              <option value="1/80">1/80</option>
              <option value="1/100">1/100</option>
              <option value="1/125">1/125</option>
              <option value="1/160">1/160</option>
              <option value="1/200">1/200</option>
              <option value="1/250">1/250</option>
              <option value="1/320">1/320</option>
              <option value="1/400">1/400</option>
              <option value="1/500">1/500</option>
              <option value="1/640">1/640</option>
              <option value="1/800">1/800</option>
              <option value="1/1000">1/1000</option>
              <option value="1/1250">1/1250</option>
              <option value="1/1600">1/1600</option>
              <option value="1/2000">1/2000</option>
              <option value="1/2500">1/2500</option>
              <option value="1/3200">1/3200</option>
              <option value="1/4000">1/4000</option>
            </select>
          </div>
        </div>
      </section>
    </main>
  </div>


</template>

<!-- Generic styles -->
<style scoped>
main {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0px;
}

.row {
  display: flex;
  flex-direction: row;
}

.container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.space-around {
  justify-content: space-around;
}

h1 {
  font-family: sans-serif;
  font-weight: lighter;
  margin-bottom: 10px;
  margin-top: 25px;
}

.vertical-gaps {
  display: flex;
  flex-direction: column;
  row-gap: 5px;
}
</style>

<!-- Reusable controls -->
<style scoped>
.labelled-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.labelled-checkbox>label {
  font-size: 20px;
}

.labelled-checkbox>input {
  width: 40px;
  height: 40px;
}

.labelled-dropdown-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px
}

.labelled-dropdown-box>label {
  font-size: 20px;
}

.labelled-dropdown-box>select {
  height: 40px;
  font-size: 20px;
}

.big-action-button {
  width: 100%;
  margin-left: 10%;
  margin-right: 10%;
  border: none;
  border-radius: 5px;
  background-color: #4CAF50;
  font-size: 24px;
}

.big-action-button:hover {
  background-color: #377e39;
}

.big-action-button:active {
  background-color: #275e29;
}

.big-action-button.active {
  background-color: rgb(211, 0, 0);
}

.labelled-textbox {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px
}

.labelled-textbox>label {
  font-size: 20px;
}

.labelled-textbox>input {
  height: 40px;
  font-size: 20px;
  width: 50%;
}
</style>

<!-- Header styles -->
<style scoped>
header {
  display: flex;
  flex-direction: row;
  width: 100%;
  gap: 10px;
  /* background-color: red; */
  height: 20px;
  flex: 0 0 20px;
}

.header-item {
  height: 100%;
}
</style>

<!-- Nav styles -->
<style scoped>
nav {
  width: 100%;
  display: flex;
  flex-direction: row;
  gap: 2px;
  height: 50px;
  flex: 0 0 50px;
}

nav button {
  width: 50%;
  height: 100%;
  background-color: #959595;
  border: none;
  font-size: 30px;
  border-radius: 10px;
}

nav button.active {
  background-color: #4CAF50;
}

nav button:hover {
  background-color: #377e39;
}

nav button:active {
  background-color: #275e29;
}
</style>

<!-- Preview styles -->
<style scoped>
#preview-viewport {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;

  display: flex;
  justify-content: center;
  align-items: center;

  cursor: grab;
}

#preview-content {
  /* width: auto;
  height: auto;
  margin: auto; */
}
</style>

<!-- Focus buttons -->
<style scoped>
.focus-button-container {
  height: 80px;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 2px;
  flex: 0 0 80px;
}

.focus-button {
  background-color: #4CAF50;
  width: 100%;
  height: 100%;
  border: none;
  color: white;
  /* padding: 15px 32px; */
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  /* margin: 4px 2px; */
  cursor: pointer;
}

.focus-button:hover {
  background-color: #3e8e41;
}

.focus-button:active {
  background-color: #347139;
}

.focus-button:disabled,
.focus-button[disabled] {
  background-color: #959595;
}
</style>

<!-- Preview settings -->
<style scoped>
#preview-settings-container {
  height: 150px;
  padding-top: 10px;
  padding-bottom: 10px;
  flex: 0 0 150px;
}
</style>