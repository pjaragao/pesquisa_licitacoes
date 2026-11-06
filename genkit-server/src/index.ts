/**
 * Servidor GenKit para Classificação de Licitações por IA
 * 
 * Este servidor expõe dois flows:
 * 1. classificarResultado - Classifica se uma licitação é adequada para a empresa
 * 2. otimizarPrompt - Melhora o prompt fornecido pelo usuário
 */

import 'dotenv/config';
import { genkit, z } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

// Carregar .env do diretório pai
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dotenv = await import('dotenv');
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

// Inicializa o GenKit com o plugin Google AI
const ai = genkit({
    plugins: [googleAI()],
});

// Schema para entrada de classificação
const ClassificacaoInputSchema = z.object({
    promptEmpresa: z.string().describe('Descrição do ramo de atividade da empresa'),
    resultado: z.object({
        id: z.number(),
        titulo: z.string().optional(),
        objeto: z.string().optional(),
        orgao: z.string().optional(),
        uf: z.string().optional(),
        modalidade: z.string().optional(),
        status: z.string().optional(),
        valorEstimado: z.string().optional(),
    }).describe('Dados da licitação a ser classificada'),
    model: z.string().optional().describe('Modelo a ser utilizado (ex: gemini-2.0-flash)'),
});

// Schema para saída de classificação
const ClassificacaoOutputSchema = z.object({
    id: z.number(),
    classificacao: z.enum(['ADEQUADO', 'NAO_ADEQUADO', 'INCERTO']),
    explicacao: z.string(),
    confianca: z.number().min(0).max(100),
});

// Schema para entrada de otimização de prompt
const OtimizarPromptInputSchema = z.object({
    promptAtual: z.string().describe('Prompt atual fornecido pelo usuário'),
});

// Schema para saída de otimização
const OtimizarPromptOutputSchema = z.object({
    promptOtimizado: z.string(),
    melhorias: z.array(z.string()),
});

// Schema para classificação em lote
const ClassificacaoLoteInputSchema = z.object({
    promptEmpresa: z.string(),
    resultados: z.array(z.object({
        id: z.number(),
        titulo: z.string().optional(),
        objeto: z.string().optional(),
        orgao: z.string().optional(),
        uf: z.string().optional(),
        modalidade: z.string().optional(),
        status: z.string().optional(),
        valorEstimado: z.string().optional(),
    })),
    model: z.string().optional().describe('Modelo a ser utilizado'),
});

const ClassificacaoLoteOutputSchema = z.object({
    classificacoes: z.array(ClassificacaoOutputSchema),
});

// ==================== FLOWS ====================

/**
 * Flow para classificar um único resultado de licitação
 */
export const classificarResultadoFlow = ai.defineFlow(
    {
        name: 'classificarResultado',
        inputSchema: ClassificacaoInputSchema,
        outputSchema: ClassificacaoOutputSchema,
    },
    async (input) => {
        const { promptEmpresa, resultado } = input;

        const prompt = `Você é um especialista em análise de licitações públicas no Brasil.

EMPRESA:
${promptEmpresa}

LICITAÇÃO A ANALISAR:
- ID: ${resultado.id}
- Título: ${resultado.titulo || 'Não informado'}
- Objeto: ${resultado.objeto || 'Não informado'}
- Órgão: ${resultado.orgao || 'Não informado'}
- UF: ${resultado.uf || 'Não informado'}
- Modalidade: ${resultado.modalidade || 'Não informado'}
- Status: ${resultado.status || 'Não informado'}
- Valor Estimado: ${resultado.valorEstimado || 'Não informado'}

TAREFA:
Analise se esta licitação é ADEQUADA para a empresa participar, considerando:
1. O objeto da licitação está alinhado com o ramo de atividade da empresa?
2. A empresa teria capacidade técnica presumida para executar?
3. Há algum indicativo de que não seria adequada?

RESPONDA EM JSON com o formato:
{
  "id": ${resultado.id},
  "classificacao": "ADEQUADO" | "NAO_ADEQUADO" | "INCERTO",
  "explicacao": "Explicação clara e objetiva em português",
  "confianca": 0-100
}`;

        const response = await ai.generate({
            model: googleAI.model(input.model || 'gemini-2.0-flash'),
            prompt,
            output: { schema: ClassificacaoOutputSchema },
        });

        return response.output ?? {
            id: resultado.id,
            classificacao: 'INCERTO' as const,
            explicacao: 'Não foi possível classificar este resultado.',
            confianca: 0,
        };
    }
);

/**
 * Flow para classificar múltiplos resultados em lote
 */
export const classificarLoteFlow = ai.defineFlow(
    {
        name: 'classificarLote',
        inputSchema: ClassificacaoLoteInputSchema,
        outputSchema: ClassificacaoLoteOutputSchema,
    },
    async (input) => {
        const { promptEmpresa, resultados } = input;

        // Formata os resultados para o prompt
        const resultadosTexto = resultados.map((r, i) => `
[${i + 1}] ID: ${r.id}
- Título: ${r.titulo || 'Não informado'}
- Objeto: ${r.objeto || 'Não informado'}
- Órgão: ${r.orgao || 'Não informado'}
- UF: ${r.uf || 'Não informado'}
- Modalidade: ${r.modalidade || 'Não informado'}
- Valor: ${r.valorEstimado || 'Não informado'}`).join('\n');

        const prompt = `Você é um especialista em análise de licitações públicas no Brasil.

EMPRESA:
${promptEmpresa}

LICITAÇÕES A ANALISAR:
${resultadosTexto}

TAREFA:
Para CADA licitação, analise se é ADEQUADA para a empresa participar.
Considere:
1. Alinhamento do objeto com o ramo de atividade
2. Capacidade técnica presumida
3. Indicativos de incompatibilidade

RESPONDA EM JSON com o formato:
{
  "classificacoes": [
    {
      "id": <id_da_licitacao>,
      "classificacao": "ADEQUADO" | "NAO_ADEQUADO" | "INCERTO",
      "explicacao": "Explicação clara",
      "confianca": 0-100
    }
  ]
}

IMPORTANTE: Retorne uma classificação para CADA licitação listada.`;

        const response = await ai.generate({
            model: googleAI.model(input.model || 'gemini-2.0-flash'),
            prompt,
            output: { schema: ClassificacaoLoteOutputSchema },
        });

        return response.output ?? { classificacoes: [] };
    }
);

/**
 * Flow para otimizar/melhorar o prompt da empresa
 */
export const otimizarPromptFlow = ai.defineFlow(
    {
        name: 'otimizarPrompt',
        inputSchema: OtimizarPromptInputSchema,
        outputSchema: OtimizarPromptOutputSchema,
    },
    async (input) => {
        const { promptAtual } = input;

        const prompt = `Você é um especialista em engenharia de prompts e análise de licitações.

PROMPT ATUAL DO USUÁRIO:
"${promptAtual}"

TAREFA:
O usuário quer usar este prompt para que uma IA classifique licitações como adequadas ou não para sua empresa.

Melhore o prompt para que seja mais eficiente na classificação, incluindo:
1. Descrição clara do ramo de atividade
2. Tipos de serviços/produtos que a empresa oferece
3. Capacidades técnicas principais
4. Regiões de atuação (se aplicável)
5. Porte da empresa (se mencionado)
6. Qualquer critério de exclusão explícito

RESPONDA EM JSON:
{
  "promptOtimizado": "O prompt melhorado e mais completo",
  "melhorias": ["Lista das melhorias aplicadas"]
}

IMPORTANTE: Mantenha a essência do que o usuário escreveu, apenas expanda e organize melhor.`;

        const response = await ai.generate({
            model: googleAI.model('gemini-2.0-flash'),
            prompt,
            output: { schema: OtimizarPromptOutputSchema },
        });

        return response.output ?? {
            promptOtimizado: promptAtual,
            melhorias: ['Não foi possível otimizar o prompt.'],
        };
    }
);

// ==================== SERVIDOR HTTP ====================

const app = express();
app.use(express.json());

// CORS para permitir chamadas do Flask
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    if (req.method === 'OPTIONS') {
        return res.sendStatus(200);
    }
    next();
});

// Endpoint para classificar um resultado
app.post('/api/classificar', async (req, res) => {
    try {
        const result = await classificarResultadoFlow(req.body);
        res.json(result);
    } catch (error: any) {
        console.error('Erro na classificação:', error);
        res.status(500).json({ error: error.message });
    }
});

// Endpoint para classificar em lote
app.post('/api/classificar-lote', async (req, res) => {
    try {
        const result = await classificarLoteFlow(req.body);
        res.json(result);
    } catch (error: any) {
        console.error('Erro na classificação em lote:', error);
        res.status(500).json({ error: error.message });
    }
});

// Endpoint para listar modelos
app.get('/api/modelos', async (req, res) => {
    try {
        const modelos = [
            { id: 'gemini-3.0-flash', name: 'Gemini 3.0 Flash (Última Geração)', type: 'flash' },
            { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', type: 'flash' },
            { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash (Estável)', type: 'flash' },
            { id: 'gemini-2.0-flash-lite-preview-02-05', name: 'Gemini 2.0 Flash-Lite', type: 'flash' },
            { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro (Análise Profunda)', type: 'pro' },
        ];
        res.json(modelos);
    } catch (error: any) {
        res.status(500).json({ error: error.message });
    }
});

// Endpoint para otimizar prompt
app.post('/api/otimizar-prompt', async (req, res) => {
    try {
        const result = await otimizarPromptFlow(req.body);
        res.json(result);
    } catch (error: any) {
        console.error('Erro na otimização:', error);
        res.status(500).json({ error: error.message });
    }
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'genkit-classificacao' });
});

const PORT = process.env.GENKIT_PORT || 3400;

app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log('🤖 Servidor GenKit - Classificação de Licitações');
    console.log('='.repeat(60));
    console.log(`🚀 Servidor rodando em http://localhost:${PORT}`);
    console.log('');
    console.log('Endpoints disponíveis:');
    console.log(`  POST /api/classificar       - Classificar um resultado`);
    console.log(`  POST /api/classificar-lote  - Classificar múltiplos resultados`);
    console.log(`  POST /api/otimizar-prompt   - Otimizar prompt da empresa`);
    console.log(`  GET  /health                - Health check`);
    console.log('');
});
