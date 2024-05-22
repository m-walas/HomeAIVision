import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";

class CameraView extends LitElement {
  @property() hass;

  render() {
    return html`
      <ha-card header="Camera View">
        <div class="card-content">
          <p>Camera view content goes here.</p>
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }
      .card-content {
        padding: 16px;
      }
    `;
  }
}

if (!customElements.get('camera-view')) {
  customElements.define('camera-view', CameraView);
}
