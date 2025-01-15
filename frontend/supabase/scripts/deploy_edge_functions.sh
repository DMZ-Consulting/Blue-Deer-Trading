#!/bin/bash

# Set the project reference
supabase link --project-ref hsnppengoffvgtnifceo

# Deploy all edge functions
supabase functions deploy trades --project-ref hsnppengoffvgtnifceo
supabase functions deploy options-strategies --project-ref hsnppengoffvgtnifceo
supabase functions deploy portfolio --project-ref hsnppengoffvgtnifceo 