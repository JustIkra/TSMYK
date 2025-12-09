# ParticipantMetricsDrawer Usage Example

## Component Props

- `modelValue` (Boolean, required) - Controls drawer open/close state (use with v-model)
- `participantId` (String, required) - UUID of the participant
- `participantName` (String, required) - Full name for the drawer title

## Usage in a View/Component

```vue
<template>
  <div>
    <!-- Trigger button -->
    <el-button @click="showMetricsDrawer = true">
      View Metrics
    </el-button>

    <!-- Drawer component -->
    <ParticipantMetricsDrawer
      v-model="showMetricsDrawer"
      :participant-id="participantId"
      :participant-name="participantName"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ParticipantMetricsDrawer from '@/components/ParticipantMetricsDrawer.vue'

const showMetricsDrawer = ref(false)
const participantId = ref('123e4567-e89b-12d3-a456-426614174000')
const participantName = ref('Иванов Иван Иванович')
</script>
```

## Features

1. **Automatic Data Loading**: Metrics are loaded automatically when the drawer opens
2. **Refresh Button**: Users can manually refresh metrics data
3. **Table Display**: Shows all participant metrics with:
   - Metric code
   - Metric name (from definitions)
   - Value (formatted with Russian locale)
   - Confidence (color-coded percentage)
   - Last updated timestamp
   - Source report indicator
4. **Empty State**: Shows helpful message when no metrics are available
5. **Loading State**: Displays spinner while fetching data
6. **Responsive**: 70% width, slides from right side

## API Calls

The component uses:
- `participantsApi.getMetrics(participantId)` - to fetch participant metrics
- `metricsApi.listMetricDefs(true)` - to fetch metric definitions for names

## Styling

The component uses:
- Element Plus CSS variables for consistency
- Color-coded confidence values (green >= 80%, orange >= 60%, red < 60%)
- Striped table for better readability
- Responsive padding and spacing
