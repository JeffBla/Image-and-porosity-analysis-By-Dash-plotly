# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkIOImage import vtkDICOMImageReader

import os
import numpy as np
import pandas as pd

import plotly.graph_objects as go
import plotly.express as px

import dash
from dash import dcc
from dash import html 
import dash_bootstrap_components as dbc
from dash_slicer import VolumeSlicer
from dash.dependencies import Input, Output, State

app = dash.Dash(__name__, update_title=None)
server = app.server

# ------------- I/O and data massaging ---------------------------------------------------
# ------------- Image  ---------------------------------------------------
inDirname = "./assets/RockCT"

reader = vtkDICOMImageReader()
reader.SetDirectoryName(inDirname)
reader.Update()

files = os.listdir(inDirname)

dcmImage_CT = np.array(reader.GetOutput().GetPointData().GetScalars()).reshape(
    len(files), reader.GetHeight(), reader.GetWidth())

Hu = dcmImage_CT

slicer = VolumeSlicer(app, Hu)
slicer.graph.figure.update_layout(
    dragmode="drawrect", newshape_line_color="cyan", plot_bgcolor="rgb(0, 0, 0)"
)
slicer.graph.config.update(
    modeBarButtonsToAdd=["drawrect", "eraseshape"]
)

slider = dcc.Slider(id="slider", max=slicer.nslices)

# Create a store with a specific ID so we can set the slicer position.
setpos_store = dcc.Store(
    id={"context": "app", "scene": slicer.scene_id, "name": "setpos"}
)

# ------------- Porosity  ---------------------------------------------------
targetCol = ['Depth (cm)',
             'Fractional porosity',
             'CTG=1095 by Computer with weight',
             'pix2pix unet 512 train 1095 test 1095',
             '512_unet512_lsgan_1095_isResetValAboveSoildCt',
             'pix2pix unet 512 train 970 test 970']

df = pd.read_excel('./assets/porosity.xlsx', 'MSCL_BH-3_15m',
                    usecols=targetCol)

axial_card = dbc.Card(
    [
        dbc.CardHeader("Image feeded AI"),
        dbc.CardBody([html.Big("BVH3_15"), html.Br(), slicer.graph, slicer.slider,setpos_store, *slicer.stores]),
        dbc.CardFooter(
            [
                html.H6(
                    [
                        "Use upper right toolbox to manipulate these images. Also, move the slider at the bottom to browse the image. ",
                        html.Br()                        
                    ]
                ),
                dbc.Tooltip(
                    "Use the slider to scroll vertically through the image and look for the ground glass occlusions.",
                    target="tooltip-target-1",
                ),
            ]
        ),
    ]
)

line_card = dbc.Card(
    [
        dbc.CardHeader("Slices of Porosity"),
        dbc.CardBody(
            [
                dcc.Dropdown([*targetCol[1:], 'All'],'Fractional porosity', id='line-dropdown'),
                dcc.Graph(
                    id="graph-line",
                    figure=px.line(df,
                        x=targetCol[0],
                        y=targetCol[1],
                        labels={"x": "Depth (cm)", "y": "Porosity"},
                        template="plotly_white",
                    ),
                    config={
                        "modeBarButtonsToAdd": [
                            "drawline",
                            "drawclosedpath",
                            "drawrect",
                            "eraseshape",
                        ]
                    }
                ),
            ]
        ),
        dbc.CardFooter(
            [
                dbc.Toast(
                    [
                        html.P(
                            "Before you can select value ranges in this histogram, you need to define a region"
                            " of interest in the slicer views above (step 1 and 2)!",
                            className="mb-0",
                        )
                    ],
                    id="roi-warning",
                    header="Please select a volume of interest first",
                    icon="danger",
                    is_open=True,
                    dismissable=False,
                ),
                "Step 3: Select a range of values to segment the occlusion. Hover on slices to find the typical "
                "values of the occlusion.",
            ]
        ),
    ]
)

app.layout = html.Div(
    [
        dbc.Container(
            [
                dbc.Row([dbc.Col(axial_card)]),
                dbc.Row([dbc.Col(line_card)]),
            ],
            fluid=True,
        ),
        dcc.Store(id="annotations", data={}),
        dcc.Store(id="occlusion-surface", data={}),
    ],
)

@app.callback(
    Output('graph-line', 'figure'),
    Input('line-dropdown', 'value')
)
def update_output(value):
    if value != 'All':
        fig = px.line(df,x=targetCol[0],
                            y=value,
                            labels={"x": "Depth (cm)", "y": "Porosity"},
                            template="plotly_white",
                        )
    else:
        fig = go.Figure()
        fig.update_layout(xaxis_title="Depth (cm)",yaxis_title = "Porosity",template="plotly_white")

        for target in targetCol[1:]:
            fig.add_trace(go.Scatter(x= df[targetCol[0]], y= df[target], mode='lines', name=target))
    return fig

@app.callback(
    Output(setpos_store.id, 'data'),
    Input('graph-line', 'clickData'))
def Click_changeImage(clickData):
    if clickData != None:
        return None,None,clickData["points"][0]['pointIndex']
    return None, None,int(len(Hu)/2)

if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_props_check=False)