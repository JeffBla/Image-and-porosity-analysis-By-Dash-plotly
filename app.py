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


def npArrAppend(np_arr, target):
    if np_arr is None:
        np_arr = target[np.newaxis, :]
    else:
        np_arr = np.append(np_arr, target[np.newaxis, :], axis=0)

    return np_arr


app = dash.Dash(__name__, update_title=None)
server = app.server


# ------------- I/O and data massaging ---------------------------------------------------
# ------------- dicom Image  ---------------------------------------------------
def DicomImage(inDirname="./assets/RockCT") -> np.array:

    reader = vtkDICOMImageReader()
    reader.SetDirectoryName(inDirname)
    reader.Update()

    files = os.listdir(inDirname)

    dcmImage_CT = np.array(
        reader.GetOutput().GetPointData().GetScalars()).reshape(
            len(files), reader.GetHeight(), reader.GetWidth())

    return dcmImage_CT


Hu = DicomImage()

slicer = VolumeSlicer(app, Hu, scene_id="rock")
slicer.graph.figure.update_layout(dragmode="drawrect",
                                  newshape_line_color="cyan",
                                  plot_bgcolor="rgb(0, 0, 0)")
slicer.graph.config.update(modeBarButtonsToAdd=["drawrect", "eraseshape"])

slider = dcc.Slider(id="slider0", max=slicer.nslices)

# Create a store with a specific ID so we can set the slicer position.
setpos_store = dcc.Store(id={
    "context": "app",
    "scene": slicer.scene_id,
    "name": "setpos"
})


# # ------------- Percent Image  ---------------------------------------------------
def PercentImage(
    inDirname_image_np='./assets/image_np/',
    inDirname_percent_np='./assets/percent_np/'
) -> (np.array, np.array, np.array, np.array):
    AIR = -1024

    imgs_np = None
    solids_np = None
    CTs_np = None
    customdatas = None

    files = os.listdir(inDirname_image_np)

    # read img
    for i in range(len(files)):
        img = np.load(inDirname_image_np + f'img_{i}.npy')
        img = img.reshape(img.shape[-2], img.shape[-1])

        ct = ((img + 1) / 2.0) * (3000 - AIR) + AIR

        percent = np.load(inDirname_percent_np + f'percent_{i}.npy').reshape(
            3, img.shape[-2], img.shape[-1])

        imgs_np = npArrAppend(imgs_np, img)
        solids_np = npArrAppend(solids_np, percent[0])
        CTs_np = npArrAppend(CTs_np, ct)

        # customdata
        customdata = np.array([ct, percent[0], percent[1], percent[2]])
        customdatas = npArrAppend(customdatas, customdata)

    return imgs_np, solids_np, CTs_np, customdata


imgs_np, solids_np, CTs_np, customdata = PercentImage()

slicer_percent = VolumeSlicer(app, solids_np * 1000, scene_id="rock")
slicer_percent.graph.figure.update_layout(dragmode="drawrect",
                                          newshape_line_color="cyan",
                                          plot_bgcolor="rgb(0, 0, 0)")

hovertemplate = "x: %{x} <br> y: %{y} <br> z: %{z} <br> ct: %{customdata[0]:.4f} <br> percent: %{customdata[1]:.4f},  %{customdata[2]:.4f}, %{customdata[3]:.4f}"
slicer_percent.graph.figure.update_traces(hoverinfo='text',
                                          customdata=customdata,
                                          hovertemplate=hovertemplate)
slicer.graph.figure.update_traces(overwrite=True,hoverinfo="text",
                                  customdata=customdata,
                                  hovertemplate=hovertemplate)

slicer_percent.graph.config.update(
    modeBarButtonsToAdd=["drawrect", "eraseshape"])

slider_percent = dcc.Slider(id="slider1", max=slicer_percent.nslices)

# Create a store with a specific ID so we can set the slicer position.
# setpos_store_percent = dcc.Store(id={
#     "context": "app",
#     "scene": slicer_percent.scene_id,
#     "name": "setpos_percent"
# })

# ------------- Porosity  ---------------------------------------------------
targetCol = [
    'Depth (cm)', 'Fractional porosity', 'CTG=1095 by Computer with weight',
    'pix2pix unet 512 train 1095 test 1095',
    '512_unet512_lsgan_1095_isResetValAboveSoildCt',
    'pix2pix unet 512 train 970 test 970'
]

df = pd.read_excel('./assets/porosity.xlsx',
                   'MSCL_BH-3_15m',
                   usecols=targetCol).iloc[:495]

axial_card = dbc.Card([
    dbc.CardHeader("Image feeded AI"),
    dbc.CardBody([
        html.Big("BVH3_15"),
        html.Br(), slicer.graph, slicer.slider, setpos_store, *slicer.stores
    ]),
    dbc.CardFooter([
        html.H6([
            "Use upper right toolbox to manipulate these images. Also, move the slider at the bottom to browse the image. ",
        ]),
        dbc.Tooltip(
            "Use the slider to scroll vertically through the image and look for the ground glass occlusions.",
            target="tooltip-target-1",
        ),
    ]),
])

percent_info_card = dbc.Card([
    dbc.CardHeader("Percentage AI give"),
    dbc.CardBody([
        html.Big("BVH3_15"),
        html.Br(), slicer_percent.graph, slicer_percent.slider,
        *slicer_percent.stores
    ]),
    dbc.CardFooter([
        html.H6([
            "Use upper right toolbox to manipulate these images. Also, move the slider at the bottom to browse the image. ",
        ]),
        dbc.Tooltip(
            "Use the slider to scroll vertically through the image and look for the ground glass occlusions.",
            target="tooltip-target-1",
        ),
    ]),
])

line_card = dbc.Card([
    dbc.CardHeader("Slices of Porosity"),
    dbc.CardBody([
        dcc.Dropdown([*targetCol[1:], 'All'],
                     'Fractional porosity',
                     id='line-dropdown'),
        dcc.Graph(id="graph-line",
                  figure=px.line(
                      df,
                      x=targetCol[0],
                      y=targetCol[1],
                      labels={
                          "x": "Depth (cm)",
                          "y": "Porosity"
                      },
                      template="plotly_white",
                  ),
                  config={
                      "modeBarButtonsToAdd": [
                          "drawline",
                          "drawclosedpath",
                          "drawrect",
                          "eraseshape",
                      ]
                  }),
    ]),
    dbc.CardFooter([
        dbc.Toast(
            [
                html.P(
                    "Click the point on the line. You can get the correspond"
                    " image.",
                    className="mb-0",
                )
            ],
            id="roi-warning",
            header="You can check the point on the line",
            icon="danger",
            is_open=True,
            dismissable=False,
        ),
        "Click the point on the line",
    ]),
])

app.layout = html.Div([
    dbc.Container(
        [
            dbc.Row([dbc.Col(axial_card),
                     dbc.Col(percent_info_card)]),
            dbc.Row([html.Hr()]),
            dbc.Row([dbc.Col(line_card)]),
        ],
        fluid=True,
    ),
    dcc.Store(id="annotations", data={}),
    dcc.Store(id="occlusion-surface", data={}),
], )


@app.callback(Output('graph-line', 'figure'), Input('line-dropdown', 'value'))
def update_output(value):
    if value != 'All':
        fig = px.line(
            df,
            x=targetCol[0],
            y=value,
            labels={
                "x": "Depth (cm)",
                "y": "Porosity"
            },
            template="plotly_white",
        )
    else:
        fig = go.Figure()
        fig.update_layout(xaxis_title="Depth (cm)",
                          yaxis_title="Porosity",
                          template="plotly_white")

        for target in targetCol[1:]:
            fig.add_trace(
                go.Scatter(x=df[targetCol[0]],
                           y=df[target],
                           mode='lines',
                           name=target))
    return fig


@app.callback(Output(setpos_store.id, 'data'), Input('graph-line',
                                                     'clickData'))
def Click_changeImage(clickData):
    if clickData != None:
        print(clickData["points"][0]['pointIndex'])
        return None, None, clickData["points"][0]['pointIndex']
    return None, int(len(Hu) / 2), int(len(Hu) / 2)


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_props_check=False)
