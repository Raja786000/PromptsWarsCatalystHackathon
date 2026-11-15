/**
 * CareCircle — Intelligent Healthcare Assistant & UX Controller
 * Features: Accessibility Controls, Voice Speech Synthesis, Modals,
 * Prescription OCR Preview, Calendar navigation, Quick Demo Fillers.
 */

// 1. Accessibility State Management
const AccessibilityManager = {
  init() {
    this.applySavedPreferences();
    this.bindEvents();
  },

  applySavedPreferences() {
    // Font scale
    const scale = localStorage.getItem('carecircle_font_scale') || '1';
    this.setFontScale(parseFloat(scale));

    // High contrast
    const contrast = localStorage.getItem('carecircle_high_contrast') === 'true';
    if (contrast) {
      document.body.classList.add('accessibility-high-contrast');
    }
  },

  setFontScale(scale) {
    document.documentElement.style.setProperty('--font-scale', scale);
    localStorage.setItem('carecircle_font_scale', scale);
    document.querySelectorAll('.acc-btn').forEach(btn => {
      btn.classList.toggle('active', parseFloat(btn.dataset.scale) === scale);
    });
  },

  toggleContrast() {
    const isContrast = document.body.classList.toggle('accessibility-high-contrast');
    localStorage.setItem('carecircle_high_contrast', isContrast);
  },

  bindEvents() {
    document.querySelectorAll('.acc-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const scale = parseFloat(btn.dataset.scale || '1');
        this.setFontScale(scale);
      });
    });

    const contrastBtn = document.getElementById('toggleContrastBtn');
    if (contrastBtn) {
      contrastBtn.addEventListener('click', () => this.toggleContrast());
    }
  }
};

// 2. Voice Speech Synthesis (Elderly Voice Reader)
const VoiceReader = {
  isSpeaking: false,

  speak(text) {
    if (!('speechSynthesis' in window)) {
      alert("Voice speech synthesis is not supported on this device/browser.");
      return;
    }

    if (this.isSpeaking) {
      window.speechSynthesis.cancel();
      this.isSpeaking = false;
      this.updateVoiceButtonState(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.88; // Slower, clear cadence for older adults
    utterance.pitch = 1.0;
    utterance.lang = 'en-US';

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.updateVoiceButtonState(true);
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.updateVoiceButtonState(false);
    };

    utterance.onerror = () => {
      this.isSpeaking = false;
      this.updateVoiceButtonState(false);
    };

    window.speechSynthesis.speak(utterance);
  },

  updateVoiceButtonState(speaking) {
    const btn = document.getElementById('voiceReadScheduleBtn');
    if (btn) {
      btn.innerHTML = speaking 
        ? '<span>⏹</span> Stop Voice Reader' 
        : '<span>🔊</span> Read Today’s Plan Aloud';
      btn.classList.toggle('active', speaking);
    }
  },

  readSchedule() {
    const summaryElem = document.getElementById('voiceScheduleContent');
    if (summaryElem) {
      const text = summaryElem.innerText || summaryElem.textContent;
      this.speak(text.trim());
    } else {
      this.speak("CareCircle daily routine: Please check your schedule card for today's medications.");
    }
  }
};

// 3. Quick Demo Login Autofill
function fillLogin(email) {
  const emailInput = document.querySelector('input[name="email"]');
  const passwordInput = document.querySelector('input[name="password"]');
  if (emailInput && passwordInput) {
    emailInput.value = email;
    passwordInput.value = 'Care123!';
    passwordInput.focus();
    
    // Highlight submission button
    const submitBtn = document.querySelector('.auth-card button[type="submit"]');
    if (submitBtn) {
      submitBtn.classList.add('pulse');
    }
  }
}

// 4. Modal Controller
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
    if (firstInput) firstInput.focus();
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// 5. Dose Logging with Note Dialog
function openDoseModal(medId, medName, schedTime, status) {
  const modal = document.getElementById('doseConfirmModal');
  if (!modal) return;

  document.getElementById('doseModalMedName').innerText = medName;
  document.getElementById('doseModalTime').innerText = schedTime.replace('T', ' at ');
  document.getElementById('doseModalStatus').value = status;
  document.getElementById('doseModalMedId').value = medId;
  document.getElementById('doseModalSched').value = schedTime;
  
  const statusBadge = document.getElementById('doseModalStatusBadge');
  if (statusBadge) {
    statusBadge.innerText = status;
    statusBadge.className = `badge badge-${status.toLowerCase()}`;
  }

  const form = document.getElementById('doseConfirmForm');
  if (form) {
    form.action = `/dose/${medId}/${status}`;
  }

  openModal('doseConfirmModal');
}

// 6. Prescription OCR Scanner Simulation
function simulatePrescriptionScan() {
  const statusElem = document.getElementById('ocrScanStatus');
  const previewBox = document.getElementById('ocrResultPreview');
  if (!statusElem || !previewBox) return;

  statusElem.style.display = 'block';
  statusElem.innerHTML = '<span class="spinner"></span> Analyzing prescription image with OCR text recognition…';

  setTimeout(() => {
    statusElem.innerHTML = '✓ OCR extraction completed. Please review and verify the details before saving.';
    previewBox.style.display = 'block';

    // Populate editable verification fields
    document.getElementById('ocrMedName').value = 'Metformin HCl';
    document.getElementById('ocrDosage').value = '500 mg';
    document.getElementById('ocrFrequency').value = 'Twice daily';
    document.getElementById('ocrTimes').value = '08:30, 19:30';
    document.getElementById('ocrInstructions').value = 'Take 1 tablet with morning and evening meals.';
    document.getElementById('ocrPrescriber').value = 'Dr. James Thorne';
  }, 1200);
}

// 7. General Event Bindings
document.addEventListener('DOMContentLoaded', () => {
  AccessibilityManager.init();

  // Voice button listener
  const voiceBtn = document.getElementById('voiceReadScheduleBtn');
  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => VoiceReader.readSchedule());
  }

  // Mobile sidebar toggle
  const sidebarToggle = document.getElementById('sidebarToggleBtn');
  const sidebar = document.querySelector('.app-sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
          sidebar.classList.remove('open');
        }
      }
    });
  }

  // Password visibility toggle
  document.querySelectorAll('.password-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.password-field-group')?.querySelector('input');
      if (input) {
        const isPass = input.type === 'password';
        input.type = isPass ? 'text' : 'password';
        btn.innerText = isPass ? '👁️' : '🙈';
      }
    });
  });

  // Modal backdrop click to close
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal(modal.id);
      }
    });
  });

  // Escape key closes modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.active').forEach(modal => {
        closeModal(modal.id);
      });
    }
  });

  // Auto-dismiss flash messages after 6 seconds
  setTimeout(() => {
    document.querySelectorAll('.flash-message').forEach(el => {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.4s ease';
      setTimeout(() => el.remove(), 400);
    });
  }, 6000);

  // Form double-submission safeguard
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
      const submitBtn = form.querySelector('button[type="submit"]:not(.no-disable)');
      if (submitBtn) {
        submitBtn.dataset.originalHtml = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Saving…';
        setTimeout(() => {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = submitBtn.dataset.originalHtml || 'Submit';
          }
        }, 4000);
      }
    });
  });
});
