<template>
  <div class="landing-page">
    <!-- Header -->
    <header class="header">
      <div class="header-container">
        <div class="header-pill">
          <div class="header-logo">
            <span class="logo-icon">ЦМ</span>
            <span class="logo-name">Цифровая модель УК</span>
          </div>

          <nav class="header-nav">
            <a
              href="#features"
              class="nav-link"
            >Возможности</a>
            <a
              href="#process"
              class="nav-link"
            >Как работает</a>
            <a
              href="#benefits"
              class="nav-link"
            >Преимущества</a>
          </nav>

          <div class="header-actions">
            <button
              class="btn-text"
              @click="router.push('/login')"
            >
              Войти
            </button>
            <button
              class="btn-primary-sm"
              @click="router.push('/register')"
            >
              Регистрация
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-container">
        <div class="hero-content">
          <h1 class="hero-title">
            Цифровая модель<br>
            <span class="text-accent">управления компетенциями</span>
          </h1>
          <p class="hero-subtitle">
            Профессиональная система оценки пригодности и развития персонала.
            Автоматизируйте процессы HR и получайте объективные результаты.
          </p>
          <div class="hero-actions">
            <button
              class="btn-primary"
              @click="router.push('/register')"
            >
              Начать работу
              <span class="btn-arrow">&#8594;</span>
            </button>
            <button
              class="btn-outline"
              @click="router.push('/login')"
            >
              Войти в систему
            </button>
          </div>
        </div>
        <div class="hero-visual">
          <div class="hero-card">
            <div class="hero-card-header">
              <div class="dots">
                <span />
                <span />
                <span />
              </div>
            </div>
            <div class="hero-card-content">
              <div class="metric-row">
                <span class="metric-label">Профпригодность</span>
                <span class="metric-value">94%</span>
              </div>
              <div class="metric-bar">
                <div
                  class="metric-fill"
                  style="width: 94%"
                />
              </div>
              <div class="metric-row">
                <span class="metric-label">Компетенции</span>
                <span class="metric-value">12/15</span>
              </div>
              <div class="metric-bar">
                <div
                  class="metric-fill"
                  style="width: 80%"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section
      id="features"
      class="features"
    >
      <div class="features-container">
        <div class="section-header">
          <span class="section-bg-text">ВОЗМОЖНОСТИ</span>
          <h2 class="section-title-light">
            Возможности <span class="text-accent">системы</span>
          </h2>
        </div>

        <div class="features-grid">
          <div class="feature-card">
            <div class="card-stripe" />
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="32">
                  <Document />
                </el-icon>
              </div>
              <h3>Автоматическая обработка отчётов</h3>
              <p>
                Загрузите отчёты в формате DOCX. Система автоматически извлечёт метрики
                с использованием Gemini Vision и AI технологий.
              </p>
              <a
                href="#"
                class="card-link"
              >
                Подробнее <span class="link-arrow">&#8594;</span>
              </a>
            </div>
          </div>

          <div class="feature-card">
            <div class="card-stripe" />
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="32">
                  <DataAnalysis />
                </el-icon>
              </div>
              <h3>Расчёт профессиональной пригодности</h3>
              <p>
                Получайте объективную оценку соответствия сотрудников требованиям
                различных профессиональных областей.
              </p>
              <a
                href="#"
                class="card-link"
              >
                Подробнее <span class="link-arrow">&#8594;</span>
              </a>
            </div>
          </div>

          <div class="feature-card">
            <div class="card-stripe" />
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="32">
                  <TrendCharts />
                </el-icon>
              </div>
              <h3>Персонализированные рекомендации</h3>
              <p>
                Система формирует индивидуальные рекомендации по развитию на основе
                выявленных сильных сторон и зон роста.
              </p>
              <a
                href="#"
                class="card-link"
              >
                Подробнее <span class="link-arrow">&#8594;</span>
              </a>
            </div>
          </div>

          <div class="feature-card">
            <div class="card-stripe" />
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="32">
                  <User />
                </el-icon>
              </div>
              <h3>Управление участниками</h3>
              <p>
                Единый реестр участников с полной историей оценок, отчётов и
                результатов анализа компетенций.
              </p>
              <a
                href="#"
                class="card-link"
              >
                Подробнее <span class="link-arrow">&#8594;</span>
              </a>
            </div>
          </div>

          <div class="feature-card">
            <div class="card-stripe" />
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="32">
                  <SetUp />
                </el-icon>
              </div>
              <h3>Гибкие весовые коэффициенты</h3>
              <p>
                Настраивайте весовые таблицы для различных профессиональных областей.
                Поддержка версионирования и аудита изменений.
              </p>
              <a
                href="#"
                class="card-link"
              >
                Подробнее <span class="link-arrow">&#8594;</span>
              </a>
            </div>
          </div>

          <div class="feature-card">
            <div class="card-stripe" />
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="32">
                  <Finished />
                </el-icon>
              </div>
              <h3>Итоговые отчёты</h3>
              <p>
                Формируйте комплексные отчёты с результатами оценки, рекомендациями
                и планами развития в удобном формате.
              </p>
              <a
                href="#"
                class="card-link"
              >
                Подробнее <span class="link-arrow">&#8594;</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Process Section -->
    <section
      id="process"
      class="process"
    >
      <div class="process-container">
        <h2 class="section-title">
          Как это <span class="text-accent">работает</span>
        </h2>

        <div class="process-steps">
          <div class="process-step">
            <div class="step-number">
              01
            </div>
            <div class="step-content">
              <h3>Загрузка данных</h3>
              <p>Загрузите отчёты участников в систему в формате DOCX</p>
            </div>
          </div>

          <div class="process-connector" />

          <div class="process-step">
            <div class="step-number">
              02
            </div>
            <div class="step-content">
              <h3>Извлечение метрик</h3>
              <p>AI автоматически распознаёт и структурирует показатели</p>
            </div>
          </div>

          <div class="process-connector" />

          <div class="process-step">
            <div class="step-number">
              03
            </div>
            <div class="step-content">
              <h3>Расчёт оценки</h3>
              <p>Вычисление профессиональной пригодности по весовым коэффициентам</p>
            </div>
          </div>

          <div class="process-connector" />

          <div class="process-step">
            <div class="step-number">
              04
            </div>
            <div class="step-content">
              <h3>Рекомендации</h3>
              <p>Получение персонализированных советов по развитию</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Benefits Section -->
    <section
      id="benefits"
      class="benefits"
    >
      <div class="benefits-container">
        <h2 class="section-title-light">
          Преимущества <span class="text-accent">платформы</span>
        </h2>

        <div class="benefits-grid">
          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon :size="24">
                <CircleCheck />
              </el-icon>
            </div>
            <div class="benefit-text">
              <h4>Автоматизация оценки</h4>
              <p>Сокращение времени на обработку данных до 90%</p>
            </div>
          </div>

          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon :size="24">
                <CircleCheck />
              </el-icon>
            </div>
            <div class="benefit-text">
              <h4>Объективность критериев</h4>
              <p>Прозрачная методология оценки без субъективизма</p>
            </div>
          </div>

          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon :size="24">
                <CircleCheck />
              </el-icon>
            </div>
            <div class="benefit-text">
              <h4>Централизованное хранение</h4>
              <p>Вся информация о сотрудниках в одном месте</p>
            </div>
          </div>

          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon :size="24">
                <CircleCheck />
              </el-icon>
            </div>
            <div class="benefit-text">
              <h4>Гибкие настройки</h4>
              <p>Версионирование весовых коэффициентов и аудит</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="cta">
      <div class="cta-container">
        <h2>Готовы начать?</h2>
        <p>Зарегистрируйтесь в системе и получите доступ к функционалу оценки компетенций</p>
        <div class="cta-actions">
          <button
            class="btn-white"
            @click="router.push('/register')"
          >
            Зарегистрироваться
            <span class="btn-arrow">&#8594;</span>
          </button>
          <button
            class="btn-white-outline"
            @click="router.push('/login')"
          >
            Войти в систему
          </button>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-container">
        <div class="footer-main">
          <div class="footer-brand">
            <div class="footer-logo">
              <span class="logo-icon-footer">ЦМ</span>
              <span class="logo-name-footer">Цифровая модель УК</span>
            </div>
            <p class="footer-description">
              Система профессиональной оценки и развития персонала.
              Автоматизация HR-процессов с использованием AI.
            </p>
          </div>

          <div class="footer-links">
            <div class="footer-column">
              <h5>Навигация</h5>
              <a href="#features">Возможности</a>
              <a href="#process">Как работает</a>
              <a href="#benefits">Преимущества</a>
            </div>
            <div class="footer-column">
              <h5>Система</h5>
              <a href="/login">Войти</a>
              <a href="/register">Регистрация</a>
            </div>
          </div>
        </div>

        <div class="footer-bottom">
          <p>&copy; 2025 Цифровая модель управления компетенциями. Версия 1.0</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import {
  Document,
  DataAnalysis,
  TrendCharts,
  User,
  SetUp,
  Finished,
  CircleCheck
} from '@element-plus/icons-vue'

const router = useRouter()
</script>

<style scoped>
/* ========================================
   BASE STYLES
   ======================================== */
.landing-page {
  background-color: var(--color-bg-page);
  overflow-x: hidden;
}

/* Accent text utility */
.text-accent {
  color: var(--color-primary);
}

/* ========================================
   HEADER
   ======================================== */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-index-fixed);
  padding: 16px 40px;
  background: var(--color-white);
  border-bottom: 1px solid var(--color-border-light);
}

.header-container {
  max-width: 1400px;
  margin: 0 auto;
}

.header-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: var(--gradient-primary);
  border-radius: var(--border-radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-white);
  font-weight: 700;
  font-size: 14px;
}

.logo-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.header-nav {
  display: flex;
  gap: 32px;
}

.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-regular);
  text-decoration: none;
  transition: var(--transition-fast);
  padding: 8px 0;
  border-bottom: 2px solid transparent;
}

.nav-link:hover {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-text {
  background: none;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-regular);
  cursor: pointer;
  padding: 10px 16px;
  transition: var(--transition-fast);
  border-radius: var(--border-radius-base);
}

.btn-text:hover {
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.btn-primary-sm {
  background: var(--color-primary);
  border: none;
  border-radius: var(--border-radius-base);
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-white);
  cursor: pointer;
  transition: var(--transition-button);
  box-shadow: var(--shadow-sm);
}

.btn-primary-sm:hover {
  background: var(--color-primary-dark);
  box-shadow: var(--shadow-md);
}

/* ========================================
   HERO SECTION
   ======================================== */
.hero {
  background: var(--gradient-hero);
  padding: 140px 40px 100px;
  min-height: 100vh;
  display: flex;
  align-items: center;
}

.hero-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
}

.hero-title {
  font-size: 52px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--color-text-primary);
  margin: 0 0 24px 0;
}

.hero-subtitle {
  font-size: 18px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  margin: 0 0 40px 0;
  max-width: 520px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--color-primary);
  border: none;
  border-radius: var(--border-radius-lg);
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 500;
  color: var(--color-white);
  cursor: pointer;
  transition: var(--transition-button);
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
  background: var(--color-primary-dark);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-lg);
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-button);
  box-shadow: var(--shadow-xs);
}

.btn-outline:hover {
  background: var(--color-gray-50);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-arrow {
  font-size: 18px;
  transition: transform 0.2s;
}

.btn-primary:hover .btn-arrow,
.btn-outline:hover .btn-arrow {
  transform: translateX(4px);
}

/* Hero Visual Card */
.hero-visual {
  display: flex;
  justify-content: center;
}

.hero-card {
  background: var(--color-white);
  border-radius: var(--border-radius-xl);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-width: 400px;
  overflow: hidden;
  border: 1px solid var(--color-border-light);
}

.hero-card-header {
  background: var(--color-gray-50);
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.dots {
  display: flex;
  gap: 6px;
}

.dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-gray-300);
}

.dots span:first-child {
  background: var(--color-danger);
}

.dots span:nth-child(2) {
  background: var(--color-warning);
}

.dots span:last-child {
  background: var(--color-success);
}

.hero-card-content {
  padding: 24px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 14px;
  color: var(--color-text-regular);
}

.metric-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.metric-bar {
  height: 8px;
  background: var(--color-gray-100);
  border-radius: var(--border-radius-sm);
  margin-bottom: 20px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: var(--border-radius-sm);
  transition: width 1s ease;
}

/* ========================================
   FEATURES SECTION
   ======================================== */
.features {
  background: var(--color-bg-section);
  padding: 100px 40px;
  position: relative;
}

.features-container {
  max-width: 1400px;
  margin: 0 auto;
}

.section-header {
  position: relative;
  text-align: center;
  margin-bottom: 60px;
}

.section-bg-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 120px;
  font-weight: 800;
  color: var(--color-primary-bg);
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
  opacity: 0.5;
}

.section-title-light {
  font-size: 40px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  position: relative;
  z-index: 1;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.feature-card {
  background: var(--color-white);
  border-radius: var(--border-radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-card);
  transition: var(--transition-base);
  border: 1px solid var(--color-border-light);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-card-hover);
}

.card-stripe {
  width: 100%;
  height: 4px;
  background: var(--gradient-primary);
  flex-shrink: 0;
}

.card-content {
  padding: 28px;
  flex: 1;
}

.card-icon {
  width: 52px;
  height: 52px;
  background: var(--color-primary-bg);
  border-radius: var(--border-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 12px 0;
}

.feature-card p {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin: 0 0 20px 0;
}

.card-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary);
  text-decoration: none;
  transition: var(--transition-fast);
}

.card-link:hover {
  color: var(--color-primary-dark);
}

.link-arrow {
  transition: transform 0.2s;
}

.card-link:hover .link-arrow {
  transform: translateX(4px);
}

/* ========================================
   PROCESS SECTION
   ======================================== */
.process {
  background: var(--color-white);
  padding: 100px 40px;
}

.process-container {
  max-width: 1400px;
  margin: 0 auto;
}

.section-title {
  font-size: 40px;
  font-weight: 700;
  color: var(--color-text-primary);
  text-align: center;
  margin: 0 0 60px 0;
}

.process-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
}

.process-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 240px;
  padding: 0 20px;
}

.step-number {
  width: 68px;
  height: 68px;
  background: var(--color-primary-bg);
  border: 2px solid var(--color-primary-light);
  border-radius: var(--border-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 24px;
  transition: var(--transition-base);
}

.process-step:hover .step-number {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-white);
}

.step-content h3 {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px 0;
}

.step-content p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-text-secondary);
  margin: 0;
}

.process-connector {
  width: 80px;
  height: 2px;
  background: var(--color-border-light);
  margin-top: 34px;
  flex-shrink: 0;
}

/* ========================================
   BENEFITS SECTION
   ======================================== */
.benefits {
  background: var(--color-gray-900);
  padding: 100px 40px;
}

.benefits-container {
  max-width: 1200px;
  margin: 0 auto;
}

.benefits-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.benefit-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--border-radius-lg);
  padding: 24px;
  transition: var(--transition-base);
}

.benefit-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--color-primary-light);
}

.benefit-icon {
  width: 44px;
  height: 44px;
  background: var(--gradient-primary);
  border-radius: var(--border-radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-white);
  flex-shrink: 0;
}

.benefit-text h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-white);
  margin: 0 0 6px 0;
}

.benefit-text p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-gray-400);
  margin: 0;
}

/* ========================================
   CTA SECTION
   ======================================== */
.cta {
  background: var(--gradient-primary);
  padding: 80px 40px;
  text-align: center;
}

.cta-container {
  max-width: 700px;
  margin: 0 auto;
}

.cta h2 {
  font-size: 38px;
  font-weight: 700;
  color: var(--color-white);
  margin: 0 0 16px 0;
}

.cta p {
  font-size: 18px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 40px 0;
}

.cta-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.btn-white {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--color-white);
  border: none;
  border-radius: var(--border-radius-lg);
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 500;
  color: var(--color-primary);
  cursor: pointer;
  transition: var(--transition-button);
  box-shadow: var(--shadow-sm);
}

.btn-white:hover {
  background: var(--color-gray-50);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-white-outline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--border-radius-lg);
  padding: 12px 28px;
  font-size: 16px;
  font-weight: 500;
  color: var(--color-white);
  cursor: pointer;
  transition: var(--transition-button);
}

.btn-white-outline:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--color-white);
}

/* ========================================
   FOOTER
   ======================================== */
.footer {
  background: var(--color-gray-900);
  padding: 60px 40px 30px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
}

.footer-main {
  display: flex;
  justify-content: space-between;
  gap: 60px;
  padding-bottom: 40px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.logo-icon-footer {
  width: 40px;
  height: 40px;
  background: var(--gradient-primary);
  border-radius: var(--border-radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-white);
  font-weight: 700;
  font-size: 14px;
}

.logo-name-footer {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-white);
}

.footer-description {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-gray-400);
  max-width: 320px;
  margin: 0;
}

.footer-links {
  display: flex;
  gap: 60px;
}

.footer-column h5 {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-white);
  margin: 0 0 16px 0;
}

.footer-column a {
  display: block;
  font-size: 14px;
  color: var(--color-gray-400);
  text-decoration: none;
  margin-bottom: 10px;
  transition: var(--transition-fast);
}

.footer-column a:hover {
  color: var(--color-primary-light);
}

.footer-bottom {
  padding-top: 30px;
  text-align: center;
}

.footer-bottom p {
  font-size: 13px;
  color: var(--color-gray-500);
  margin: 0;
}

/* ========================================
   RESPONSIVE DESIGN
   ======================================== */
@media (max-width: 1200px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-title {
    font-size: 44px;
  }
}

@media (max-width: 992px) {
  .hero-container {
    grid-template-columns: 1fr;
    gap: 60px;
  }

  .hero-visual {
    order: -1;
  }

  .hero-content {
    text-align: center;
  }

  .hero-subtitle {
    margin-left: auto;
    margin-right: auto;
  }

  .hero-actions {
    justify-content: center;
  }

  .process-steps {
    flex-wrap: wrap;
    gap: 40px;
  }

  .process-connector {
    display: none;
  }

  .benefits-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .header {
    padding: 12px 20px;
  }

  .header-pill {
    padding: 0;
  }

  .header-nav {
    display: none;
  }

  .logo-name {
    display: none;
  }

  .hero {
    padding: 100px 20px 60px;
  }

  .hero-title {
    font-size: 32px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .section-title,
  .section-title-light {
    font-size: 28px;
  }

  .section-bg-text {
    font-size: 60px;
  }

  .features,
  .process,
  .benefits,
  .cta {
    padding: 60px 20px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .process-steps {
    flex-direction: column;
    align-items: center;
  }

  .process-step {
    max-width: 300px;
  }

  .cta h2 {
    font-size: 28px;
  }

  .footer-main {
    flex-direction: column;
    gap: 40px;
  }

  .footer-links {
    gap: 40px;
  }

  .footer {
    padding: 40px 20px 20px;
  }
}

@media (max-width: 480px) {
  .hero-title {
    font-size: 26px;
  }

  .hero-actions {
    flex-direction: column;
    width: 100%;
  }

  .btn-primary,
  .btn-outline {
    width: 100%;
    justify-content: center;
  }

  .cta-actions {
    flex-direction: column;
  }

  .btn-white,
  .btn-white-outline {
    width: 100%;
    justify-content: center;
  }
}
</style>
