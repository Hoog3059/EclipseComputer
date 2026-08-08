<script setup>
import { onMounted, ref } from "vue";
import WZoom from "vanilla-js-wheel-zoom";

const base_url = import.meta.env.VITE_SERVER_BASE;

const focus_enabled = ref(false);
const live_preview_enabled_instead_of_last_image = ref(true);

const server_connected = ref(false);
const camera_connected = ref(false);

const viewfinder = ref(false);
const preview_capture = ref(false);

const batterylevel = ref("0%");

const iso = ref("0");
const shutterspeed = ref("0");
const aperture = ref("0");

onMounted(() => {
  var frame = document.getElementById('preview-viewport');
  var wzoom = WZoom.create('#preview-content', {
    type: 'image',
    maxScale: 10,
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
  document.getElementById("livePreviewCheckbox").checked = live_preview_enabled_instead_of_last_image.value;
});

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
    viewfinder.value = data.viewfinder;
    preview_capture.value = data.preview_capture;
    batterylevel.value = data.batterylevel;
    iso.value = data.iso;
    shutterspeed.value = data.shutterspeed;
    aperture.value = data.aperture;
  } catch (error) {
    server_connected.value = false;
    console.error('Error fetching camera status:', error);
  }
}

setInterval(fetchStatus, 1000);

// setInterval(() => {
//   var timestamp = new Date().getTime();
//   var imageContent = document.querySelector("#preview-content");
//   imageContent.src = 'http://' + base_url + ':5000/preview_feed?t=' + timestamp;
// }, 4000);

async function sendFocusCommand(command) {
  try {
    const response = await fetch(`http://${base_url}:5000/camera/manualfocus/${command}`, {
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

async function previewCheckboxChanged(checkbox) {
  if(checkbox.srcElement.checked) {
    await fetch(`http://${base_url}:5000/camera/start_preview`);
  } else {
    await fetch(`http://${base_url}:5000/camera/stop_preview`);
    await fetch(`http://${base_url}:5000/camera/stop_viewfinder`);
  }
}

async function startTotalityBurst() {
  await fetch(`http://${base_url}:5000/camera/totality_image_burst`)
}

function livePreviewCheckboxClicked(event) {
  var livePreviewCheckbox = document.getElementById("livePreviewCheckbox");
  var lastImageCheckbox = document.getElementById("lastImageCheckbox");
  var checked = event.srcElement.checked;

  live_preview_enabled_instead_of_last_image.value = checked;
  lastImageCheckbox.checked = !checked;
}

function lastImageCheckboxClicked(event) {
  var livePreviewCheckbox = document.getElementById("livePreviewCheckbox");
  var lastImageCheckbox = document.getElementById("lastImageCheckbox");
  var checked = event.srcElement.checked;

  live_preview_enabled_instead_of_last_image.value = !checked;
  livePreviewCheckbox.checked = !checked;
}

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
    <main>
      <div id="preview-switcher">
        Live preview
        <input id="livePreviewCheckbox" type="checkbox" @click="livePreviewCheckboxClicked"/>
        <input id="lastImageCheckbox" type="checkbox" @click="lastImageCheckboxClicked"/>
        Last image
      </div>
      <div id="preview-viewport" v-show="live_preview_enabled_instead_of_last_image">
        <div id="preview-placeholder">
          No feed available...
        </div>
        <img id="preview-content" :src="'http://' + base_url + ':5000/preview_feed'" />
      </div>
    </main>
    <footer>
      <div class="focus-button-container">
        <button :disabled="!focus_enabled" class="focus-button"
          @click="sendFocusCommand('near_3')">&lt;&lt;&lt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('near_2')">&lt;&lt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('near_1')">&lt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('far_1')">&gt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('far_2')">&gt;&gt;</button>
        <button :disabled="!focus_enabled" class="focus-button" @click="sendFocusCommand('far_3')">&gt;&gt;&gt;</button>
      </div>
      <div class="capture-settings-container">
        <div class="column-1">
          <div class="labelled-checkbox">
            <label>Enable focus</label>
            <input type="checkbox" v-model="focus_enabled" />
          </div>
          <div class="labelled-checkbox">
            <label>Enable preview</label>
            <input type="checkbox" v-model="preview_capture" @click="previewCheckboxChanged"/>
          </div>

          <button @click="startTotalityBurst">Start totality burst</button>
        </div>
        <div class="column-1">
          <div class="settings-selector-box">
            <p>ISO:</p>
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

          <div class="settings-selector-box">
            <p>Shutter Speed:</p>
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

          <div class="settings-selector-box">
            <p>Aperture:</p>
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




      </div>
    </footer>
  </div>


</template>

<style scoped>
.labelled-checkbox {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
}

.labelled-checkbox>input {
  width: 20px;
  height: 20px
}

.container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

header {
  display: flex;
  flex-direction: row;
  width: 100%;
  gap: 10px;
  /* background-color: red; */
  height: 20px;
}

.header-item {
  height: 100%;
}

main {
  background-color: #f0f0f0;
  flex: 1 1 auto;
  overflow: auto;
}

.capture-settings-container {
  height: 50%;
  align-items: center;
  justify-content: center;
  display: flex;
  flex-direction: row;
}

.capture-settings-container>.column-1 {
  display: flex;
  flex-direction: column;
  width: 50%;
}

.settings-selector-box {
  display: flex;
  flex-direction: row;
}

#preview-viewport {
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
  /* border:1px solid black; */
}

#preview-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 24px;
  color: #888;
  z-index: -10;
}

/* #rotate-preview-button {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
} */

footer {
  flex: 0 0 auto;
  height: 400px;
  width: 100%;
}

.focus-button-container {
  width: 100%;
  height: 20%;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 2px;
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
