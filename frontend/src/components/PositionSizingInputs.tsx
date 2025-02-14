import { Input } from "./ui/input";
import { Card, CardContent } from "./ui/card";
import { PositionSizingConfig } from '../types/position-sizing';
import { useState, useEffect } from 'react';

interface PositionSizingInputsProps {
  config: PositionSizingConfig;
  onChange: (config: PositionSizingConfig) => void;
}

interface ValidationErrors {
  portfolioSize?: string;
  riskTolerancePercent?: string;
}

export function PositionSizingInputs({ config, onChange }: PositionSizingInputsProps) {
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validate = (name: string, value: number) => {
    if (name === 'portfolioSize') {
      if (value <= 0) return 'Portfolio size must be greater than 0';
      if (value > 1000000000) return 'Portfolio size must be less than 1 billion';
    }
    if (name === 'riskTolerancePercent') {
      if (value <= 0) return 'Risk tolerance must be greater than 0';
      if (value > 100) return 'Risk tolerance must be less than 100%';
    }
    return undefined;
  };

  const handleChange = (name: keyof PositionSizingConfig, value: number) => {
    const error = validate(name, value);
    setErrors(prev => ({ ...prev, [name]: error }));
    setTouched(prev => ({ ...prev, [name]: true }));
    
    if (!error) {
      onChange({
        ...config,
        [name]: value
      });
    }
  };

  return (
    <Card className="mb-4">
      <CardContent className="flex gap-4 p-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Portfolio Size ($)
          </label>
          <Input
            type="number"
            min="0"
            value={config.portfolioSize}
            onChange={(e) => handleChange('portfolioSize', parseFloat(e.target.value) || 0)}
            onBlur={() => setTouched(prev => ({ ...prev, portfolioSize: true }))}
            className={`w-full ${touched.portfolioSize && errors.portfolioSize ? 'border-red-500' : ''}`}
          />
          {touched.portfolioSize && errors.portfolioSize && (
            <p className="mt-1 text-sm text-red-500">{errors.portfolioSize}</p>
          )}
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Risk Tolerance (%)
          </label>
          <Input
            type="number"
            step="0.1"
            min="0"
            max="100"
            value={config.riskTolerancePercent}
            onChange={(e) => handleChange('riskTolerancePercent', parseFloat(e.target.value) || 0)}
            onBlur={() => setTouched(prev => ({ ...prev, riskTolerancePercent: true }))}
            className={`w-full ${touched.riskTolerancePercent && errors.riskTolerancePercent ? 'border-red-500' : ''}`}
          />
          {touched.riskTolerancePercent && errors.riskTolerancePercent && (
            <p className="mt-1 text-sm text-red-500">{errors.riskTolerancePercent}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 