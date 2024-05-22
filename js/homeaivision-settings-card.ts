import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";

class HomeAIVisionSettingsCard extends LitElement {
  @property() hass;

  render() {
    return html`
      <ha-card header="Home AI Vision Settings">
        <div class="card-content">
          <p>Settings content goes here.</p>
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

if (!customElements.get('homeaivision-settings-card')) {
  customElements.define('homeaivision-settings-card', HomeAIVisionSettingsCard);
}
