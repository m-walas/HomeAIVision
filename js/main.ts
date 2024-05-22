import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";
import "./camera-view";
import "./query-counter";
import "./homeaivision-settings-card";

class HomeAIVisionPanel extends LitElement {
  @property() hass;
  @property() narrow;
  @property() connection;

  render() {
    return html`
      <ha-top-app-bar-fixed>
        <ha-menu-button slot="navigationIcon" .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div slot="title">Home AI Vision</div>
        <div slot="actionItems">
          <a href="https://github.com/m-walas/HomeAIVision" target="_blank">
            <ha-icon class="icon" .icon=${"mdi:help-circle"}></ha-icon>
          </a>
        </div>

        <ha-config-section .narrow=${this.narrow} full-width>
          <camera-view .hass=${this.hass}></camera-view>
          <query-counter .hass=${this.hass}></query-counter>
          <homeaivision-settings-card .hass=${this.hass}></homeaivision-settings-card>
        </ha-config-section>
      </ha-top-app-bar-fixed>
    `;
  }

  static get styles() {
    return css`
      :host {
        --app-header-background-color: var(--sidebar-background-color);
        --app-header-text-color: var(--sidebar-text-color);
        --app-header-border-bottom: 1px solid var(--divider-color);
        --ha-card-border-radius: var(--ha-config-card-border-radius, 8px);
      }
      ha-config-section {
        padding: 16px 0;
        direction: ltr;
      }
      a {
        color: var(--primary-text-color);
        text-decoration: none;
      }
    `;
  }
}

customElements.define("homeaivision-panel", HomeAIVisionPanel);
